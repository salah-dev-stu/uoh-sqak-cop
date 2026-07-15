"""Step-0 signed fairness declaration (FR-F4, F5)."""

from __future__ import annotations

from cipherchase.peer.declaration import build_declaration, verify_declaration

KW = {
    "team": "uoh-sqak",
    "players": ["Salah Qadah:323039974", "Andalus Kalash:211435797"],
    "role": "police",
    "git_commit": "deadbeef",
    "llm": {"provider": "template", "model": "template", "version": "n/a"},
    "system": {"os": "macOS", "cpu": "M2", "ram_gb": 8.0, "gpu": "Apple Silicon"},
    "version": "1.00",
}


def test_declaration_carries_all_required_fields() -> None:
    decl = build_declaration(**KW)
    for key in ("team", "players", "role", "git_commit", "llm", "system", "version", "signature"):
        assert key in decl


def test_declaration_signature_verifies() -> None:
    assert verify_declaration(build_declaration(**KW)) is True


def test_tampering_any_field_breaks_the_signature() -> None:
    decl = build_declaration(**KW)
    decl["git_commit"] = "forged"
    assert verify_declaration(decl) is False
