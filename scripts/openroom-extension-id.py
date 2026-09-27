#!/usr/bin/env python3
"""Derive a Chromium/Chrome extension ID from an RSA key.

Chromium computes an extension's ID as the SHA-256 hash of the DER-encoded
SubjectPublicKeyInfo of its public key, truncated to the first 16 bytes,
with each hex nibble mapped from 0-9,a-f to the letters a-p. Computing this
ahead of packing lets the same ID be baked into both the
ExtensionInstallForcelist policy and the self-hosted update manifest.
"""
import argparse
import hashlib
import sys

from cryptography.hazmat.primitives import serialization

_NIBBLE_TO_LETTER = "abcdefghijklmnop"


def _extension_id_from_public_der(der: bytes) -> str:
    digest = hashlib.sha256(der).digest()[:16]
    return "".join(
        _NIBBLE_TO_LETTER[nibble]
        for byte in digest
        for nibble in (byte >> 4, byte & 0x0F)
    )


def extension_id_from_pem(pem_bytes: bytes) -> str:
    if b"PRIVATE KEY" in pem_bytes:
        key = serialization.load_pem_private_key(pem_bytes, password=None)
        public_key = key.public_key()
    else:
        public_key = serialization.load_pem_public_key(pem_bytes)

    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return _extension_id_from_public_der(der)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key_file", help="PEM-encoded RSA private or public key")
    args = parser.parse_args()

    with open(args.key_file, "rb") as f:
        ext_id = extension_id_from_pem(f.read())

    print(ext_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
