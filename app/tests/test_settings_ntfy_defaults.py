"""SettingsService 推送相关 DEFAULTS 单测。"""
from app.services.settings_service import SettingsService


def test_ntfy_defaults_present() -> None:
    d = SettingsService.DEFAULTS
    assert d["ntfy_enabled"] == "0"
    assert d["ntfy_topic"] == ""
    assert d["ntfy_server"] == "https://ntfy.sh"
