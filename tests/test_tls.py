from hannah_webui.tls import ensure_self_signed_certificate


def test_generates_cert_and_key(tmp_path):
    cert_file = tmp_path / "tls" / "cert.pem"
    key_file = tmp_path / "tls" / "key.pem"

    ensure_self_signed_certificate(cert_file, key_file)

    assert cert_file.exists()
    assert key_file.exists()
    assert cert_file.read_text(encoding="utf-8").startswith("-----BEGIN CERTIFICATE-----")
    assert key_file.read_text(encoding="utf-8").startswith("-----BEGIN PRIVATE KEY-----")


def test_does_not_regenerate_existing_pair(tmp_path):
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"

    ensure_self_signed_certificate(cert_file, key_file)
    original_cert = cert_file.read_bytes()
    original_key = key_file.read_bytes()

    ensure_self_signed_certificate(cert_file, key_file)

    assert cert_file.read_bytes() == original_cert
    assert key_file.read_bytes() == original_key
