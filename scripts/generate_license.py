"""Seller-only tool: generate the signing keypair once, then turn buyer
request codes into activation codes. This is the ONLY place the private
key is ever loaded -- it lives at ~/.jobmind-license-signing/private_key.pem
(outside the repo entirely, never committed, never shipped in the app).
app/services/license_crypto.py holds only the public key and can verify
signatures but never produce new ones.
"""
from __future__ import annotations

import argparse
import base64
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.services.license_crypto import (  # noqa: E402
    _normalize_code,
    format_activation_code,
    REQUEST_PREFIX,
)


def default_key_path() -> Path:
    return Path.home() / ".jobmind-license-signing" / "private_key.pem"


def default_ledger_path() -> Path:
    return Path.home() / ".jobmind-license-signing" / "issued_licenses.log"


def _record_issued_license(ledger_path: Path, customer_name: str, request_code: str, activation_code: str) -> None:
    # Local-only record of who a key was issued to, for the seller's own
    # reference (support, "did I already send this customer a key",
    # eventual revocation lists) -- never read by the app itself, never
    # shipped, lives next to the private key outside the repo.
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp}\t{customer_name}\t{request_code}\t{activation_code}\n")


def init_keys(key_path: Path) -> int:
    if key_path.exists():
        print(f"A private key already exists at {key_path}.")
        print("Refusing to overwrite it -- delete it yourself first if you really want a new one")
        print("(every license activated with the old key would stop verifying).")
        return 1

    key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    key_path.write_bytes(pem)
    try:
        key_path.chmod(0o600)
    except OSError:
        pass  # best-effort on platforms without POSIX permission bits (Windows)

    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    public_b64 = base64.b64encode(public_bytes).decode("ascii")

    print(f"Private key written to: {key_path}")
    print("This file is the ONLY copy -- back it up somewhere safe and private.")
    print("Never commit it, never copy it into the app's source tree.")
    print()
    print("Paste this into app/services/license_crypto.py's PUBLIC_KEY_B64:")
    print()
    print(f'    PUBLIC_KEY_B64 = "{public_b64}"')
    return 0


def sign_request_code(key_path: Path, ledger_path: Path, customer_name: str, request_code: str) -> int:
    if not key_path.exists():
        print(f"ERROR: no private key found at {key_path}")
        print("Run with --init-keys first.")
        return 1

    normalized = _normalize_code(request_code)
    if not normalized.startswith(REQUEST_PREFIX):
        print(f"ERROR: request code should start with {REQUEST_PREFIX}- (got: {request_code!r})")
        return 1

    private_key = load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        print(f"ERROR: key at {key_path} is not an Ed25519 private key")
        return 1

    signature = private_key.sign(normalized.encode("utf-8"))
    activation_code = format_activation_code(signature)
    _record_issued_license(ledger_path, customer_name, request_code, activation_code)
    print(activation_code)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="JobMind Match seller tool: sign a buyer's request code into an activation code."
    )
    parser.add_argument(
        "customer_name", nargs="?", help="Customer name/email -- recorded in the local issued-licenses ledger only"
    )
    parser.add_argument(
        "request_code", nargs="?", help=f"Buyer request code ({REQUEST_PREFIX}-XXXXX-XXXXX-XXXX)"
    )
    parser.add_argument(
        "--init-keys", action="store_true", help="Generate a new signing keypair (run this once, ever)"
    )
    parser.add_argument(
        "--key-path", type=Path, default=None, help="Override the private key path (default: ~/.jobmind-license-signing/private_key.pem)"
    )
    parser.add_argument(
        "--ledger-path", type=Path, default=None, help="Override the issued-licenses ledger path (default: ~/.jobmind-license-signing/issued_licenses.log)"
    )
    args = parser.parse_args()

    key_path = args.key_path or default_key_path()
    ledger_path = args.ledger_path or default_ledger_path()

    if args.init_keys:
        return init_keys(key_path)

    if not args.customer_name or not args.request_code:
        parser.print_help()
        return 1

    return sign_request_code(key_path, ledger_path, args.customer_name, args.request_code)


if __name__ == "__main__":
    raise SystemExit(main())
