"""
Unit tests for EncryptionService.

Tests encryption/decryption functionality, error handling, and security properties.
Target coverage: 100% for this critical security component.
"""

import pytest

from src.exceptions import EncryptionError
from src.core.encryption import EncryptionService


class TestEncryptionService:
    """Test suite for EncryptionService."""

    def test_encrypt_then_decrypt_returns_original(self) -> None:
        """Test that encrypting then decrypting returns the original plaintext."""
        service = EncryptionService()
        plaintext = "DE89370400440532013000"

        # Encrypt then decrypt
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertexts(self) -> None:
        """Test that same plaintext produces different ciphertexts (due to random IV)."""
        service = EncryptionService()
        plaintext = "DE89370400440532013000"

        # Encrypt same plaintext twice
        ciphertext1 = service.encrypt(plaintext)
        ciphertext2 = service.encrypt(plaintext)

        # Ciphertexts should be different (Fernet includes timestamp and random IV)
        assert ciphertext1 != ciphertext2

        # But both should decrypt to same plaintext
        assert service.decrypt(ciphertext1) == plaintext
        assert service.decrypt(ciphertext2) == plaintext

    def test_encrypt_empty_string_returns_empty_string(self) -> None:
        """Test that empty string is not encrypted (returns empty string)."""
        service = EncryptionService()

        ciphertext = service.encrypt("")

        assert ciphertext == ""

    def test_decrypt_empty_string_returns_empty_string(self) -> None:
        """Test that empty string decryption returns empty string."""
        service = EncryptionService()

        plaintext = service.decrypt("")

        assert plaintext == ""

    def test_decrypt_tampered_ciphertext_raises_error(self) -> None:
        """Test that decrypting tampered ciphertext raises EncryptionError."""
        service = EncryptionService()
        plaintext = "DE89370400440532013000"

        # Encrypt valid plaintext
        ciphertext = service.encrypt(plaintext)

        # Tamper with ciphertext (flip one character)
        if ciphertext[0] == "A":
            tampered_ciphertext = "B" + ciphertext[1:]
        else:
            tampered_ciphertext = "A" + ciphertext[1:]

        # Decryption should fail with EncryptionError
        with pytest.raises(EncryptionError, match="invalid or tampered"):
            service.decrypt(tampered_ciphertext)

    def test_decrypt_invalid_token_raises_error(self) -> None:
        """Test that decrypting invalid token raises EncryptionError."""
        service = EncryptionService()

        # Invalid Fernet token
        invalid_token = "invalid_base64_token"

        with pytest.raises(EncryptionError, match="Failed to decrypt data"):
            service.decrypt(invalid_token)

    def test_key_derivation_is_deterministic(self) -> None:
        """Test that same SECRET_KEY produces same encryption key."""
        service1 = EncryptionService()
        service2 = EncryptionService()

        plaintext = "DE89370400440532013000"

        # Encrypt with first service instance
        ciphertext = service1.encrypt(plaintext)

        # Decrypt with second service instance (should work)
        decrypted = service2.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_unicode_characters(self) -> None:
        """Test encryption and decryption of unicode characters."""
        service = EncryptionService()
        plaintext = "Über Bänk €1000 账户"

        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_long_string(self) -> None:
        """Test encryption and decryption of long string."""
        service = EncryptionService()
        # Long IBAN-like string
        plaintext = "DE89370400440532013000" * 10  # 220 characters

        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)

        assert decrypted == plaintext
        assert len(ciphertext) > len(plaintext)  # Encrypted data is longer

    def test_encrypt_special_characters(self) -> None:
        """Test encryption of special characters."""
        service = EncryptionService()
        plaintext = "Account #123 - User's IBAN: GB82 WEST 1234 5698 7654 32"

        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_ciphertext_is_url_safe_base64(self) -> None:
        """Test that ciphertext is URL-safe base64 (Fernet format)."""
        service = EncryptionService()
        plaintext = "DE89370400440532013000"

        ciphertext = service.encrypt(plaintext)

        # Fernet tokens are URL-safe base64 (no +, /, or = padding issues)
        # Should only contain: A-Z, a-z, 0-9, -, _
        import re

        assert re.match(r"^[A-Za-z0-9_-]+={0,2}$", ciphertext)
