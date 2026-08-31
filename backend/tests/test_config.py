from __future__ import annotations

from iterlab.config import Settings


def _settings(**env: str) -> Settings:
    return Settings(_env_file=None, jwt_secret="x", **env)  # type: ignore[call-arg]


def test_cors_origins_parses_comma_separated_env_string() -> None:
    s = _settings(cors_origins="http://localhost:3000,https://app.example")
    assert s.cors_origins == ["http://localhost:3000", "https://app.example"]


def test_cors_origins_default_is_a_list() -> None:
    assert _settings().cors_origins == ["http://localhost:3000"]


def test_cors_origins_accepts_a_list_directly() -> None:
    s = _settings(cors_origins=["https://a", "https://b"])
    assert s.cors_origins == ["https://a", "https://b"]
