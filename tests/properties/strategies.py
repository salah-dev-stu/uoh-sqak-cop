"""Shared hypothesis strategies for the property suite (JSON-able payloads)."""

from __future__ import annotations

from hypothesis import strategies as st

json_values = st.recursive(
    st.none() | st.booleans() | st.integers(-10**6, 10**6)
    | st.floats(allow_nan=False, allow_infinity=False) | st.text(max_size=20),
    lambda kids: st.lists(kids, max_size=4) | st.dictionaries(st.text(max_size=10), kids, max_size=4),
    max_leaves=12,
)

payloads = st.dictionaries(st.text(min_size=1, max_size=10), json_values, max_size=6)


def bump_hex(text: str, index: int) -> str:
    """Replace the hex char at ``index`` with the next hex digit (always different)."""
    ch = text[index]
    return text[:index] + format((int(ch, 16) + 1) % 16, "x") + text[index + 1:]
