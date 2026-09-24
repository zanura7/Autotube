import os
from pathlib import Path
from typing import Optional, Union

from cryptography.fernet import Fernet, InvalidToken

from src.db.database import DATA_DIR


class SecretStore:
    """Encrypt stream credentials before they are persisted."""

    def __init__(self, key: Optional[Union[str, bytes]] = None):
        resolved_key = key or os.getenv("AUTOTUBE_SECRET_KEY")
        if not resolved_key:
            resolved_key = self._development_key()
        if isinstance(resolved_key, str):
            resolved_key = resolved_key.encode("ascii")
        try:
            self._fernet = Fernet(resolved_key)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "AUTOTUBE_SECRET_KEY must be a valid Fernet key. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            ) from exc

    @staticmethod
    def _development_key() -> bytes:
        if os.getenv("AUTOTUBE_ENV", "development").lower() == "production":
            raise RuntimeError("AUTOTUBE_SECRET_KEY is required in production.")

        key_path = Path(DATA_DIR) / ".secret_key"
        if key_path.exists():
            return key_path.read_bytes().strip()

        key = Fernet.generate_key()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
        try:
            key_path.chmod(0o600)
        except OSError:
            pass
        return key

    def encrypt(self, value: str) -> str:
        if not value:
            raise ValueError("Cannot encrypt an empty value.")
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError(
                "Stored credential cannot be decrypted with the configured key."
            ) from exc
