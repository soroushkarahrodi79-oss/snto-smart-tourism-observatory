"""Unit tests for the shared Earth Engine foundation (ADR-015).

Fully offline: ``ee`` is replaced with a fresh mock module per test via
``sys.modules`` (the repo's established convention). No test contacts Google
Earth Engine or requires credentials.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from src.config.settings import Settings
from src.integrations.earth_engine import client as ee_client
from src.integrations.earth_engine.client import (
    EarthEngineClient,
    get_change_explorer_client,
    initialize_earth_engine,
    reset_earth_engine_state,
)
from src.integrations.earth_engine.errors import (
    EarthEngineAuthError,
    EarthEngineConfigError,
    EarthEngineDisabledError,
    EarthEngineError,
    EarthEngineQuotaError,
    EarthEngineUnavailableError,
    map_ee_exception,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ee() -> MagicMock:
    """Install a fresh mock ``ee`` module and clear the process init guard.

    Yields the mock so tests can assert on ``ee.Initialize`` /
    ``ee.ServiceAccountCredentials`` calls. Both the module and the guard are
    restored afterwards so tests stay isolated.
    """
    reset_earth_engine_state()
    saved = sys.modules.get("ee")

    ee = types.ModuleType("ee")
    ee.Initialize = MagicMock()
    ee.ServiceAccountCredentials = MagicMock(return_value="fake-creds")
    sys.modules["ee"] = ee
    try:
        yield ee  # type: ignore[misc]
    finally:
        reset_earth_engine_state()
        if saved is not None:
            sys.modules["ee"] = saved
        else:  # pragma: no cover - depends on test ordering
            sys.modules.pop("ee", None)


def _enabled_settings(**over: object) -> Settings:
    base: dict[str, object] = {
        "snto_enable_change_explorer": True,
        "gee_project_id": "snto-test",
        "gee_service_account": "",
        "gee_key_file": "",
    }
    base.update(over)
    return Settings(**base)  # type: ignore[arg-type]


# ── Feature flag ──────────────────────────────────────────────────────────────

class TestFeatureFlag:
    def test_default_is_false(self):
        assert Settings().snto_enable_change_explorer is False

    def test_env_override_enables(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SNTO_ENABLE_CHANGE_EXPLORER", "true")
        assert Settings().snto_enable_change_explorer is True


# ── Low-level initialization ──────────────────────────────────────────────────

class TestInitializeEarthEngine:
    def test_personal_auth(self, mock_ee: MagicMock):
        result = initialize_earth_engine("snto-test")  # no key_file
        assert isinstance(result, EarthEngineClient)
        assert result.project_id == "snto-test"
        mock_ee.Initialize.assert_called_once_with(project="snto-test")
        mock_ee.ServiceAccountCredentials.assert_not_called()

    def test_service_account_auth(self, mock_ee: MagicMock):
        initialize_earth_engine(
            "snto-test",
            service_account="svc@snto.iam.gserviceaccount.com",
            key_file="/secret/key.json",
        )
        mock_ee.ServiceAccountCredentials.assert_called_once_with(
            "svc@snto.iam.gserviceaccount.com", "/secret/key.json"
        )
        mock_ee.Initialize.assert_called_once_with(
            credentials="fake-creds", project="snto-test"
        )

    def test_missing_project_raises_config_error(self, mock_ee: MagicMock):
        with pytest.raises(EarthEngineConfigError):
            initialize_earth_engine("")
        mock_ee.Initialize.assert_not_called()

    def test_idempotent_same_credentials(self, mock_ee: MagicMock):
        initialize_earth_engine("snto-test", key_file="/secret/key.json")
        initialize_earth_engine("snto-test", key_file="/secret/key.json")
        initialize_earth_engine("snto-test", key_file="/secret/key.json")
        assert mock_ee.Initialize.call_count == 1

    def test_reinitializes_after_state_reset(self, mock_ee: MagicMock):
        initialize_earth_engine("snto-test")
        reset_earth_engine_state()
        initialize_earth_engine("snto-test")
        assert mock_ee.Initialize.call_count == 2


# ── Application-facing accessor ───────────────────────────────────────────────

class TestGetChangeExplorerClient:
    def test_disabled_flag_raises(self, mock_ee: MagicMock):
        s = Settings(snto_enable_change_explorer=False, gee_project_id="snto-test")
        with pytest.raises(EarthEngineDisabledError):
            get_change_explorer_client(s)
        mock_ee.Initialize.assert_not_called()

    def test_enabled_but_no_project_raises_config_error(self, mock_ee: MagicMock):
        s = Settings(snto_enable_change_explorer=True, gee_project_id="")
        with pytest.raises(EarthEngineConfigError):
            get_change_explorer_client(s)
        mock_ee.Initialize.assert_not_called()

    def test_enabled_personal_auth_initializes(self, mock_ee: MagicMock):
        client = get_change_explorer_client(_enabled_settings())
        assert client.project_id == "snto-test"
        mock_ee.Initialize.assert_called_once_with(project="snto-test")

    def test_no_repeated_init_across_calls(self, mock_ee: MagicMock):
        s = _enabled_settings()
        get_change_explorer_client(s)
        get_change_explorer_client(s)
        assert mock_ee.Initialize.call_count == 1


# ── Safe exception mapping ────────────────────────────────────────────────────

class TestExceptionMapping:
    def test_quota_maps_to_quota_error(self):
        mapped = map_ee_exception(RuntimeError("Quota exceeded for this project"))
        assert isinstance(mapped, EarthEngineQuotaError)

    def test_auth_maps_to_auth_error(self):
        mapped = map_ee_exception(RuntimeError("403 permission denied"))
        assert isinstance(mapped, EarthEngineAuthError)

    def test_unknown_maps_to_unavailable(self):
        mapped = map_ee_exception(RuntimeError("backend hiccup"))
        assert isinstance(mapped, EarthEngineUnavailableError)

    def test_all_mapped_are_earth_engine_errors(self):
        for exc in (
            RuntimeError("rate limit"),
            RuntimeError("unauthorized"),
            RuntimeError("something else"),
        ):
            assert isinstance(map_ee_exception(exc), EarthEngineError)

    def test_no_credential_leak_in_message(self, mock_ee: MagicMock):
        secret_path = "/secret/super-secret-key.json"
        svc = "svc@snto.iam.gserviceaccount.com"
        mock_ee.Initialize.side_effect = RuntimeError(
            f"auth failed reading {secret_path} for {svc}"
        )
        with pytest.raises(EarthEngineAuthError) as excinfo:
            initialize_earth_engine(
                "snto-test", service_account=svc, key_file=secret_path
            )
        message = str(excinfo.value)
        assert secret_path not in message
        assert svc not in message
        # Original is retained only via chaining for local debugging.
        assert excinfo.value.__cause__ is not None

    def test_init_failure_maps_to_typed_error(self, mock_ee: MagicMock):
        mock_ee.Initialize.side_effect = RuntimeError("some backend failure")
        with pytest.raises(EarthEngineUnavailableError):
            initialize_earth_engine("snto-test")


# ── GEEAdapter now consumes the shared foundation ─────────────────────────────

class TestGeeAdapterUsesSharedInit:
    def test_adapter_initialize_delegates_to_foundation(self, mock_ee: MagicMock):
        from src.assets.models import (
            AssetType,
            GeoJSONGeometry,
            GeometryType,
            TourismAsset,
        )
        from src.ingestion.gee_adapter import GEEAdapter

        adapter = GEEAdapter(project_id="snto-test")  # personal auth (no key_file)
        adapter._initialize()

        assert adapter._initialized is True
        mock_ee.Initialize.assert_called_once_with(project="snto-test")
        # Second call is a no-op (adapter guard + process guard).
        adapter._initialize()
        assert mock_ee.Initialize.call_count == 1

        # Sanity: the adapter still builds and the fixture types import cleanly.
        _ = TourismAsset(
            asset_id="t1",
            name="x",
            asset_type=AssetType.TRAIL,
            geometry=GeoJSONGeometry(
                type=GeometryType.LINESTRING, coordinates=[[-3.5, 41.1], [-3.4, 41.2]]
            ),
            region="r",
        )

    def test_adapter_service_account_mode(self, mock_ee: MagicMock):
        from src.ingestion.gee_adapter import GEEAdapter

        adapter = GEEAdapter(project_id="snto-test", key_file="/secret/key.json")
        adapter._initialize()
        # Preserves the previous email="" positional behaviour (service_account="").
        mock_ee.ServiceAccountCredentials.assert_called_once_with(
            "", "/secret/key.json"
        )
        mock_ee.Initialize.assert_called_once_with(
            credentials="fake-creds", project="snto-test"
        )


# ── earthengine-api absence ───────────────────────────────────────────────────

class TestMissingSdk:
    def test_missing_package_raises_unavailable(self, monkeypatch: pytest.MonkeyPatch):
        reset_earth_engine_state()

        def _boom() -> object:
            raise EarthEngineUnavailableError("earthengine-api is not installed.")

        # Simulate the lazy import failing.
        monkeypatch.setattr(ee_client, "_import_ee", _boom)
        with pytest.raises(EarthEngineUnavailableError):
            initialize_earth_engine("snto-test")
        # Still a RuntimeError subclass — preserves the adapter's old contract.
        assert issubclass(EarthEngineUnavailableError, RuntimeError)
        reset_earth_engine_state()
