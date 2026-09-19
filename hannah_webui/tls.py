"""Self-signed TLS certificate generation for native HTTPS termination (#61).

The Telegram Login Widget flow (account linking in /me) requires HTTPS.
Telegram itself never validates the certificate's CA chain, so a self-signed
certificate is sufficient — no reverse proxy / Let's Encrypt required for
LAN-only deployments that have no way to obtain one anyway.
"""
from __future__ import annotations

import datetime
import logging
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

log = logging.getLogger("hannah_webui")

# ~500 years — long enough that expiry is a non-issue, so a user's client-side
# trust decision (e.g. "always trust this certificate" in a browser) never
# gets invalidated by renewal.
_VALIDITY = datetime.timedelta(days=500 * 365)


def ensure_self_signed_certificate(cert_file: str | Path, key_file: str | Path) -> None:
    """Generate a self-signed certificate + private key if they don't exist yet.

    Never regenerates an existing pair — restarting the service must not
    invalidate a certificate a user already marked as trusted.
    """
    cert_path = Path(cert_file)
    key_path = Path(key_file)

    if cert_path.exists() and key_path.exists():
        return

    log.info("Generating self-signed TLS certificate at %s (valid ~500 years)", cert_path)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "hannah-webui")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + _VALIDITY)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
