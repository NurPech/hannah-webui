import os

import pytest

from hannah_webui.config import load


@pytest.fixture
def clean_tls_env(monkeypatch):
    for name in ("HANNAH_WEBUI_TLS_ENABLED", "HANNAH_WEBUI_TLS_CERT_FILE", "HANNAH_WEBUI_TLS_KEY_FILE"):
        monkeypatch.delenv(name, raising=False)


def test_tls_defaults_disabled(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("secret_key: abc\n", encoding="utf-8")

    cfg = load(config_file)

    assert cfg.tls.enabled is False
    assert cfg.tls.cert_file == "/var/lib/hannah-webui/tls/cert.pem"
    assert cfg.tls.key_file == "/var/lib/hannah-webui/tls/key.pem"


def test_tls_explicit_cert_key_from_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "tls:\n  enabled: true\n  cert_file: /custom/cert.pem\n  key_file: /custom/key.pem\n",
        encoding="utf-8",
    )

    cfg = load(config_file)

    assert cfg.tls.enabled is True
    assert cfg.tls.cert_file == "/custom/cert.pem"
    assert cfg.tls.key_file == "/custom/key.pem"


def test_tls_from_env(monkeypatch, tmp_path, clean_tls_env):
    monkeypatch.setenv("HANNAH_WEBUI_TLS_ENABLED", "true")

    cfg = load(tmp_path / "does-not-exist.yaml")

    assert cfg.tls.enabled is True
    assert cfg.tls.cert_file == "/data/tls/cert.pem"
    assert cfg.tls.key_file == "/data/tls/key.pem"


def test_tls_env_disabled_by_default(tmp_path, clean_tls_env):
    cfg = load(tmp_path / "does-not-exist.yaml")

    assert cfg.tls.enabled is False


def test_tls_explicit_cert_key_from_env(monkeypatch, tmp_path, clean_tls_env):
    monkeypatch.setenv("HANNAH_WEBUI_TLS_CERT_FILE", "/custom/cert.pem")
    monkeypatch.setenv("HANNAH_WEBUI_TLS_KEY_FILE", "/custom/key.pem")

    cfg = load(tmp_path / "does-not-exist.yaml")

    assert cfg.tls.cert_file == "/custom/cert.pem"
    assert cfg.tls.key_file == "/custom/key.pem"
