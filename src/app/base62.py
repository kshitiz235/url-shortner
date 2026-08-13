"""
Base-62 encoding.

Turns a non-negative integer (our row id) into a short, URL-safe string using
62 symbols: 0-9, a-z, A-Z. This is how we get compact, collision-free short
codes: because each row id is unique, each encoded code is unique too — no
random guessing, no retry loop.

Think of it exactly like writing a number in base 10, but with 62 available
"digits" instead of 10.
"""

# The 62 symbols. Their ORDER defines the encoding — don't reorder it later,
# or previously issued codes would decode to different numbers.
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62

# Reverse lookup: symbol -> its value. Built once for fast decoding.
_INDEX = {char: value for value, char in enumerate(ALPHABET)}


def encode(number: int) -> str:
    """Encode a non-negative integer as a base-62 string."""
    if number < 0:
        raise ValueError("number must be non-negative")
    if number == 0:
        return ALPHABET[0]

    digits = []
    while number > 0:
        number, remainder = divmod(number, BASE)  # split off the last "digit"
        digits.append(ALPHABET[remainder])
    # We built it least-significant-digit first, so reverse it.
    return "".join(reversed(digits))


def decode(code: str) -> int:
    """Inverse of `encode`: turn a base-62 string back into its integer.

    Not needed for redirects (we look codes up in the DB), but it lets us prove
    the encoding is a correct round-trip in tests.
    """
    number = 0
    for char in code:
        if char not in _INDEX:
            raise ValueError(f"invalid base-62 character: {char!r}")
        number = number * BASE + _INDEX[char]
    return number
