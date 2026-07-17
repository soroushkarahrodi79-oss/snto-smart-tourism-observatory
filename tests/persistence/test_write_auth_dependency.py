from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.api.v2.deps import require_write_auth
from src.config.settings import Settings, settings


def test_api_key_defaults_empty() -> None:
    assert Settings(_env_file=None).snto_api_key == ""


def test_auth_disabled_returns_actor(monkeypatch) -> None:
    monkeypatch.setattr(settings, "snto_api_key", "")
    assert require_write_auth(x_api_key=None, x_actor="gestor") == "gestor"
    assert require_write_auth(x_api_key=None, x_actor=None) == "anonymous"


def test_auth_enabled_requires_valid_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "snto_api_key", "s3cret")
    with pytest.raises(HTTPException) as exc:
        require_write_auth(x_api_key=None, x_actor=None)
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException):
        require_write_auth(x_api_key="wrong", x_actor=None)


def test_auth_enabled_valid_key_resolves_actor(monkeypatch) -> None:
    monkeypatch.setattr(settings, "snto_api_key", "s3cret")
    assert require_write_auth(x_api_key="s3cret", x_actor="gestor") == "gestor"
    assert require_write_auth(x_api_key="s3cret", x_actor=None) == "api-key"
