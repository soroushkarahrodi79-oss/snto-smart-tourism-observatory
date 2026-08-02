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
        # Email + key forwarded as SDK keywords (verified against the real
        # ee._helpers.ServiceAccountCredentials signature).
        mock_ee.ServiceAccountCredentials.assert_called_once_with(
            email="svc@snto.iam.gserviceaccount.com", key_file="/secret/key.json"
        )
        mock_ee.Initialize.assert_called_once_with(
            credentials="fake-creds", project="snto-test"
        )

    def test_json_key_without_email_passes_none(self, mock_ee: MagicMock):
        # A JSON key carries its own client_email; the SDK ignores `email`. We
        # forward None (its documented default), never an empty-string issuer.
        initialize_earth_engine("snto-test", key_file="/secret/key.json")
        mock_ee.ServiceAccountCredentials.assert_called_once_with(
            email=None, key_file="/secret/key.json"
        )

    def test_service_account_without_key_file_is_config_error(self, mock_ee: MagicMock):
        # Email set but no key file: reject clearly instead of silently using
        # personal auth and ignoring the operator's intent.
        with pytest.raises(EarthEngineConfigError):
            initialize_earth_engine(
                "snto-test", service_account="svc@x.iam", key_file=""
            )
        mock_ee.Initialize.assert_not_called()
        mock_ee.ServiceAccountCredentials.assert_not_called()

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

    def test_switching_credential_sets_reinitializes(self, mock_ee: MagicMock):
        # A → B → A must re-init each time it switches: the single-slot guard
        # never wrongly skips because EE is global (one active context at a time).
        initialize_earth_engine("proj-a")
        initialize_earth_engine("proj-b")
        initialize_earth_engine("proj-a")
        assert mock_ee.Initialize.call_count == 3
        # Same set twice in a row is still a no-op.
        initialize_earth_engine("proj-a")
        assert mock_ee.Initialize.call_count == 3

    def test_failed_init_is_not_recorded_as_initialized(self, mock_ee: MagicMock):
        mock_ee.Initialize.side_effect = RuntimeError("backend down")
        with pytest.raises(EarthEngineUnavailableError):
            initialize_earth_engine("snto-test")
        # A failed init must NOT mark the set initialised — a retry must re-attempt.
        mock_ee.Initialize.side_effect = None
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
    # Representative real-world EE / Google API messages -> expected category.
    @pytest.mark.parametrize(
        "message, expected",
        [
            # Quota / rate limiting
            ("Quota exceeded for quota metric 'EECU'", EarthEngineQuotaError),
            ("User rate limit exceeded.", EarthEngineQuotaError),
            ("429 Too Many Requests", EarthEngineQuotaError),
            # Authentication / permission / project registration
            ("Unauthorized", EarthEngineAuthError),
            ("403 Caller does not have permission", EarthEngineAuthError),
            ("Invalid credentials provided", EarthEngineAuthError),
            ("Request had invalid authentication credentials", EarthEngineAuthError),
            # Transient / generic availability failures
            ("Connection reset by peer", EarthEngineUnavailableError),
            ("SSL: CERTIFICATE_VERIFY_FAILED", EarthEngineUnavailableError),
            ("Computation timed out", EarthEngineUnavailableError),
            ("Internal server error", EarthEngineUnavailableError),
        ],
    )
    def test_classification(self, message: str, expected: type):
        assert isinstance(map_ee_exception(RuntimeError(message)), expected)

    def test_auth_message_is_not_misclassified_as_quota(self):
        # An auth failure must never come back as a quota error.
        for msg in ("403 Forbidden", "unauthenticated request", "permission denied"):
            mapped = map_ee_exception(RuntimeError(msg))
            assert not isinstance(mapped, EarthEngineQuotaError)

    def test_bare_rate_does_not_trigger_quota(self):
        # "rate" alone (e.g. a data-rate note) must not be read as rate-limiting.
        mapped = map_ee_exception(RuntimeError("sample rate mismatch in asset"))
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
        # The adapter has no service-account email field; the JSON key carries its
        # own client_email, so email is forwarded as None (the SDK default).
        mock_ee.ServiceAccountCredentials.assert_called_once_with(
            email=None, key_file="/secret/key.json"
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


# ── Streamlit cache boundary ──────────────────────────────────────────────────

class TestCachedAccessor:
    def test_importable_without_streamlit_runtime(self):
        # The cached accessor is built at import (Streamlit is a declared dep) but
        # nothing here requires a *run context*; it is a plain callable.
        assert callable(ee_client.cached_earth_engine_client)

    def test_disabled_state_not_cached_as_success(
        self, mock_ee: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        # Deterministic start: clear guard + Streamlit memo.
        reset_earth_engine_state()

        # 1) Disabled global settings -> the accessor raises (not a cached client).
        monkeypatch.setattr(
            ee_client,
            "_default_settings",
            Settings(snto_enable_change_explorer=False, gee_project_id="snto-test"),
        )
        with pytest.raises(EarthEngineDisabledError):
            ee_client.cached_earth_engine_client()
        mock_ee.Initialize.assert_not_called()

        # 2) Enable: the earlier failure must NOT have been memoised as success.
        monkeypatch.setattr(ee_client, "_default_settings", _enabled_settings())
        client = ee_client.cached_earth_engine_client()
        assert client.project_id == "snto-test"

        # Leave no cached success behind for other tests.
        reset_earth_engine_state()
