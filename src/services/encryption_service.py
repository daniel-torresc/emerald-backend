"""
Encryption service for sensitive data (IBAN, etc.).

Uses Fernet (AES-128-CBC + HMAC) for authenticated encryption.
Key is derived from SECRET_KEY using PBKDF2-HMAC-SHA256.

SECURITY NOTES:
- All encrypted data includes authentication tag (tamper-proof)
- Key derivation uses 100,000 iterations (OWASP recommended minimum)
- Changing SECRET_KEY will make all existing encrypted data undecryptable
- Never log plaintext data or encryption keys
"""

import base64
import logging

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.core.config import settings
from src.exceptions import EncryptionError

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.

    Uses Fernet (symmetric encryption) with key derived from SECRET_KEY.
    All encrypted data is authenticated (tamper-proof).

    Key derivation:
        - Algorithm: PBKDF2-HMAC-SHA256
        - Iterations: 100,000 (OWASP recommended minimum)
        - Salt: Static application-specific salt
        - Output: 32-byte key for Fernet

    Encryption format:
        - Fernet token (URL-safe base64)
        - Includes: timestamp, IV, ciphertext, HMAC
        - Authenticated encryption (integrity + confidentiality)
    """

    def __init__(self) -> None:
        """
        Initialize encryption service with derived key.

        Raises:
            ValueError: If SECRET_KEY is not set or key derivation fails
        """
        try:
            # Derive encryption key from SECRET_KEY using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"emerald-iban-encryption-salt",  # Static salt for deterministic key
                iterations=100000,  # OWASP recommended minimum
            )
            key_material = kdf.derive(settings.secret_key.encode())
            key = base64.urlsafe_b64encode(key_material)
            self.cipher = Fernet(key)
            logger.info("Encryption service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {e}")
            raise ValueError("Encryption service initialization failed") from e

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt (e.g., IBAN)

        Returns:
            Encrypted string (base64-encoded Fernet token)

        Raises:
            EncryptionError: If encryption fails

        Example:
            >>> service = EncryptionService()
            >>> encrypted = service.encrypt("DE89370400440532013000")
            >>> # Returns: "gAAAAABl..."
        """
        if not plaintext:
            return ""

        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError("Failed to encrypt data") from e

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Encrypted string (Fernet token)

        Returns:
            Decrypted plaintext string

        Raises:
            EncryptionError: If decryption fails (invalid token, tampered data)

        Example:
            >>> service = EncryptionService()
            >>> plaintext = service.decrypt("gAAAAABl...")
            >>> # Returns: "DE89370400440532013000"
        """
        if not ciphertext:
            return ""

        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("Decryption failed: Invalid or tampered ciphertext")
            raise EncryptionError(
                "Failed to decrypt data (invalid or tampered)"
            ) from None
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError("Failed to decrypt data") from e
