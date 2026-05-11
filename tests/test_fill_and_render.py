"""Tests for scripts/fill_and_render.py's build_context() — the slot-validation
gate that guards the .docx renderer against ID mismatches between writer output
and template-config.yaml.

We deliberately don't test the docxtpl render or docx2pdf step — those are
external deps that need a real .docx and Word installed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _import_fill_and_render():
    """Load scripts/fill_and_render.py as a module without going through __main__."""
    path = PROJECT_ROOT / "scripts" / "fill_and_render.py"
    spec = importlib.util.spec_from_file_location("fill_and_render", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["fill_and_render"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fr():
    return _import_fill_and_render()


def _config():
    return {
        "roles": [
            {"id": "ai_engineer", "bullet_count": 3},
            {"id": "scada_engineer", "bullet_count": 2},
        ],
        "projects": [
            {"id": "rag", "bullet_count": 3},
            {"id": "resume_agent", "bullet_count": 4},
        ],
        "skills": {
            "categories": ["Languages", "AI&ML", "Concepts & Tools"],
            "max_per_category": 8,
        },
    }


def _bullets():
    return {
        "roles": [
            {"role_id": "ai_engineer", "bullets": ["B1", "B2", "B3"]},
            {"role_id": "scada_engineer", "bullets": ["S1", "S2"]},
        ],
        "projects": [
            {"project_id": "rag", "bullets": ["R1", "R2", "R3"]},
            {"project_id": "resume_agent", "bullets": ["P1", "P2", "P3", "P4"]},
        ],
        "skills": {
            "Languages": ["Python", "Bash"],
            "AI&ML": ["RAG", "Prompting"],
            "Concepts & Tools": ["Docker", "FastAPI"],
        },
    }


def test_build_context_happy_path(fr):
    ctx = fr.build_context(_bullets(), _config())
    assert ctx["ai_engineer_bullets"] == ["B1", "B2", "B3"]
    assert ctx["scada_engineer_bullets"] == ["S1", "S2"]
    assert ctx["rag_bullets"] == ["R1", "R2", "R3"]
    assert ctx["resume_agent_bullets"] == ["P1", "P2", "P3", "P4"]


def test_build_context_skills_joined_correctly(fr):
    ctx = fr.build_context(_bullets(), _config())
    assert ctx["skills_languages"] == "Python, Bash"
    assert ctx["skills_aiml"] == "RAG, Prompting"
    assert ctx["skills_concepts_tools"] == "Docker, FastAPI"


def test_build_context_unknown_role_id_exits(fr):
    bullets = _bullets()
    bullets["roles"].append({"role_id": "made_up_role", "bullets": ["X"]})
    with pytest.raises(SystemExit, match="made_up_role"):
        fr.build_context(bullets, _config())


def test_build_context_unknown_project_id_exits(fr):
    bullets = _bullets()
    bullets["projects"].append({"project_id": "ghost_project", "bullets": ["X"]})
    with pytest.raises(SystemExit, match="ghost_project"):
        fr.build_context(bullets, _config())


def test_build_context_missing_skills_category_yields_empty_string(fr):
    bullets = _bullets()
    bullets["skills"] = {"Languages": ["Python"]}  # AI&ML and Concepts & Tools missing
    ctx = fr.build_context(bullets, _config())
    assert ctx["skills_languages"] == "Python"
    assert ctx["skills_aiml"] == ""
    assert ctx["skills_concepts_tools"] == ""


def test_build_context_empty_bullets_lists_pass_through(fr):
    """If a slot has zero bullets, the for-loop renders nothing — that's valid."""
    bullets = _bullets()
    bullets["roles"][0]["bullets"] = []
    ctx = fr.build_context(bullets, _config())
    assert ctx["ai_engineer_bullets"] == []
