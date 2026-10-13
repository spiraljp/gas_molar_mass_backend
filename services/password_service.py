import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        salt, password_hash = stored_password_hash.split("$", 1)
    except ValueError:
        return False

    checked_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()

    return secrets.compare_digest(checked_hash, password_hash)
