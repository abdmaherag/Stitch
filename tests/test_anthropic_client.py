"""Tests for the JSON-extraction layer in anthropic_client.

We don't hit the real API — we stub the Anthropic client.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from resume_test.anthropic_client import (
    Stage,
    _parse_json_lenient,
    call_json,
)


def _make_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def _make_client(*texts: str):
    """Returns a stub Anthropic client whose .messages.create() yields the given
    response texts in sequence."""
    client = MagicMock()
    responses = [_make_response(t) for t in texts]
    client.messages.create.side_effect = responses
    return client


def _stage():
    return Stage(name="test", model="claude-sonnet-4-6", system_prompt="x", max_tokens=100)


def test_parse_json_lenient_plain():
    assert _parse_json_lenient('{"a": 1}') == {"a": 1}


def test_parse_json_lenient_strips_code_fence():
    text = '```json\n{"a": 1}\n```'
    assert _parse_json_lenient(text) == {"a": 1}


def test_parse_json_lenient_strips_unlabeled_fence():
    text = '```\n{"a": 1}\n```'
    assert _parse_json_lenient(text) == {"a": 1}


def test_parse_json_lenient_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        _parse_json_lenient("not json")


def test_call_json_succeeds_first_try():
    client = _make_client('{"verdict": "approve"}')
    result = call_json(client, _stage(), "user")
    assert result == {"verdict": "approve"}
    assert client.messages.create.call_count == 1


def test_call_json_retries_on_invalid_then_succeeds():
    client = _make_client("garbage", '{"verdict": "approve"}')
    result = call_json(client, _stage(), "user")
    assert result == {"verdict": "approve"}
    assert client.messages.create.call_count == 2


def test_call_json_raises_after_two_failures():
    client = _make_client("garbage", "still garbage")
    with pytest.raises(RuntimeError, match="failed to produce valid JSON after retry"):
        call_json(client, _stage(), "user")
    assert client.messages.create.call_count == 2
