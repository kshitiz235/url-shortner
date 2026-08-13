"""
Unit tests for the base-62 encoder.

These test the encoding in isolation (no database, no web) — the fastest kind
of test and a good habit: pure logic gets pure unit tests.
"""
import pytest

from src.app import base62


def test_known_values():
    assert base62.encode(0) == "0"
    assert base62.encode(1) == "1"
    assert base62.encode(61) == "Z"      # last single-digit symbol
    assert base62.encode(62) == "10"     # rolls over to two digits


def test_round_trip():
    """encode then decode should return the original number, for many values."""
    for n in [0, 1, 7, 61, 62, 125, 9999, 1_000_000, 56_800_235_584]:
        assert base62.decode(base62.encode(n)) == n


def test_encode_rejects_negative():
    with pytest.raises(ValueError):
        base62.encode(-1)


def test_decode_rejects_invalid_char():
    with pytest.raises(ValueError):
        base62.decode("abc$")


def test_codes_are_url_safe():
    """No characters that would need escaping in a URL path."""
    code = base62.encode(123_456_789)
    assert code.isalnum()
