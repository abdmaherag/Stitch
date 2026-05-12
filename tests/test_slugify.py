"""Tests for slugify — must produce filesystem-safe, ATS-friendly company slugs."""

from __future__ import annotations

import pytest

from stitch.slugify import slugify


@pytest.mark.parametrize("name, expected", [
    ("Acme", "acme"),
    ("Acme Corp", "acme-corp"),
    ("Al Atheer Group", "al-atheer-group"),
    ("Goldman Sachs", "goldman-sachs"),
    ("OpenAI", "openai"),
    ("  acme  ", "acme"),
    ("ACME!", "acme"),
    ("Müller & Co.", "muller-co"),
    ("Foo / Bar / Baz", "foo-bar-baz"),
    ("---weird---input---", "weird-input"),
    ("Company (NYC)", "company-nyc"),
    ("123 Industries", "123-industries"),
])
def test_slugify_normalizes(name, expected):
    assert slugify(name) == expected


def test_slugify_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        slugify("")


def test_slugify_whitespace_only_raises():
    with pytest.raises(ValueError, match="empty"):
        slugify("   ")


def test_slugify_punctuation_only_raises():
    with pytest.raises(ValueError, match="empty slug"):
        slugify("!!!")
