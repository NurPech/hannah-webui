from unittest.mock import patch

from hannah_webui import log_shipping
from hannah_webui.config import Config, GrpcConfig


def test_config_secrets_finds_nested_secret_values_only():
    cfg = {
        "server": {"host": "0.0.0.0", "port": 8080},
        "nested": {"api_key": "abc123", "keep": "public"},
        "items": [{"password": "pw"}],
    }
    assert list(log_shipping.config_secrets(cfg)) == ["abc123", "pw"]


def test_config_secrets_reads_the_config_dataclass():
    cfg = Config(
        secret_key="flask-secret",
        telegram_bot_token="bot-token",
        telegram_bot_username="hannah_bot",
        entra_client_id="client-id",
        entra_client_secret="entra-secret",
    )
    assert sorted(log_shipping.config_secrets(cfg)) == ["bot-token", "entra-secret", "flask-secret"]


def test_config_secrets_skips_empty_values():
    assert list(log_shipping.config_secrets(Config())) == []


def test_install_passes_component_address_and_secrets():
    cfg = Config(secret_key="flask-secret")

    with patch("hannah_logging.install") as install:
        log_shipping.install("2.9.1", hannah_address="core:50051", cfg=cfg)

    kwargs = install.call_args.kwargs
    assert kwargs["component"] == "webui"
    assert kwargs["version"] == "2.9.1"
    assert kwargs["hannah_address"] == "core:50051"
    assert kwargs["secrets"] == ["flask-secret"]


def test_setup_uses_grpc_address_from_config():
    cfg = Config(grpc=GrpcConfig(host="hannah-core", port=50052))

    with patch("hannah_logging.install") as install:
        log_shipping.setup(cfg)

    assert install.call_args.kwargs["hannah_address"] == "hannah-core:50052"
