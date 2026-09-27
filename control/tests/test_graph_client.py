import datetime
import socket

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.graph_client import GraphCalendarClient


def _network_available() -> bool:
    try:
        socket.create_connection(("login.microsoftonline.com", 443), timeout=3).close()
        return True
    except OSError:
        return False


# msal.ConfidentialClientApplication.__init__ performs OIDC tenant
# discovery over the network immediately (this is the exact behaviour
# calendar.py's CalendarPoller was fixed to handle defensively) — there's
# no way to construct one, valid cert or not, fully offline. "common" is
# Microsoft's stable multi-tenant discovery alias, so this only tests
# certificate handling, not any particular tenant.
pytestmark = pytest.mark.skipif(
    not _network_available(),
    reason="requires network access to login.microsoftonline.com for OIDC tenant discovery",
)

TEST_TENANT = "common"


def _self_signed_cert_and_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "openroom-test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        )
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return cert_pem, key_pem


def test_valid_certificate_and_key_construct_a_client():
    cert_pem, key_pem = _self_signed_cert_and_key()
    # Doesn't raise: msal validates and loads the certificate (deriving
    # its own SHA-256 thumbprint) at construction time.
    GraphCalendarClient(
        tenant_id=TEST_TENANT,
        client_id="client",
        certificate_pem=cert_pem,
        private_key_pem=key_pem,
        room_mailbox_upn="room@example.com",
    )


def test_invalid_certificate_raises():
    _, key_pem = _self_signed_cert_and_key()
    with pytest.raises(ValueError):
        GraphCalendarClient(
            tenant_id=TEST_TENANT,
            client_id="client",
            certificate_pem="not a real certificate",
            private_key_pem=key_pem,
            room_mailbox_upn="room@example.com",
        )
