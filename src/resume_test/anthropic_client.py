"""Thin wrapper over the Anthropic SDK with prompt caching, JSON-extraction,
and one-shot retry on parse failure.

The system prompts (analyzer / writer / reviewer .md files) are reused across
the pipeline run, so we mark them with `cache_control` to drop input cost on
later calls. The cache TTL is 5 minutes — well within a pipeline run.

Auth: supports BOTH OAuth (recommended — bills against Claude Code subscription,
no separate API charges) AND raw API key. Resolution order:
  1. ANTHROPIC_AUTH_TOKEN (OAuth)  — generate via `claude setup-token`
  2. ANTHROPIC_API_KEY  (direct API billing)
If neither is set, raises a clear error pointing at both options.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from anthropic import Anthropic


# Model IDs — see CLAUDE.md / PRD.md for the rationale on the split.
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_OPUS = "claude-opus-4-7"


def make_client() -> Anthropic:
    """Build an Anthropic client using whichever auth is available.

    Prefers OAuth (ANTHROPIC_AUTH_TOKEN, generated via `claude setup-token`)
    because it bills against the Claude Code subscription rather than
    metering separate API tokens. Falls back to ANTHROPIC_API_KEY.
    """
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if auth_token:
        return Anthropic(auth_token=auth_token)
    if api_key:
        return Anthropic(api_key=api_key)

    raise RuntimeError(
        "No Anthropic auth found. Set one of:\n"
        "  ANTHROPIC_AUTH_TOKEN  (recommended — uses your Claude Code subscription;\n"
        "                         generate via `claude setup-token`)\n"
        "  ANTHROPIC_API_KEY     (direct API billing)\n"
        "Or run via the Claude Code skill (`/resume-test`) which uses your\n"
        "session's OAuth automatically with zero env setup."
    )


@dataclass(frozen=True)
class Stage:
    """A single LLM call's configuration."""

    name: str            # "analyzer" | "writer" | "reviewer"
    model: str           # one of MODEL_SONNET / MODEL_OPUS
    system_prompt: str   # full prompt text (will be cached)
    max_tokens: int


def call(
    client: Anthropic,
    stage: Stage,
    user_message: str,
) -> str:
    """One LLM call, returns the raw text content of the response.

    System prompt is sent with `cache_control: ephemeral` so subsequent
    identical system prompts (same stage re-invoked, e.g. on revision pass)
    hit the cache.
    """
    response = client.messages.create(
        model=stage.model,
        max_tokens=stage.max_tokens,
        system=[
            {
                "type": "text",
                "text": stage.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )
    parts = [block.text for block in response.content if block.type == "text"]
    return "".join(parts).strip()


def call_json(
    client: Anthropic,
    stage: Stage,
    user_message: str,
) -> dict:
    """Like `call`, but parses the response as JSON.

    The agents are instructed to emit raw JSON (no code fences, no commentary),
    but models occasionally wrap output in ```json fences anyway. We strip
    those before parsing. On parse failure, retry once with an explicit
    "your previous response wasn't valid JSON" follow-up.
    """
    raw = call(client, stage, user_message)
    try:
        return _parse_json_lenient(raw)
    except json.JSONDecodeError as first_err:
        retry_message = (
            f"{user_message}\n\n"
            "Your previous response was not valid JSON. Return only the JSON "
            "object — no markdown fences, no commentary, no leading/trailing text."
        )
        raw = call(client, stage, retry_message)
        try:
            return _parse_json_lenient(raw)
        except json.JSONDecodeError as second_err:
            raise RuntimeError(
                f"Stage {stage.name!r} failed to produce valid JSON after retry. "
                f"First error: {first_err}. Second error: {second_err}. "
                f"Last raw output: {raw[:500]!r}"
            ) from second_err


_CODE_FENCE = re.compile(r"^```(?:json)?\s*\n(.*?)\n```\s*$", re.DOTALL)


def _parse_json_lenient(text: str) -> dict:
    """Strip code fences if present, then json.loads."""
    text = text.strip()
    fence_match = _CODE_FENCE.match(text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)
