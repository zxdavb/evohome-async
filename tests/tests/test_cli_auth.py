"""Tests for evohome-async CLI authentication and credential storage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from _evohome.exceptions import CredentialStorageError
from evohome_cli.auth import KeyringCredentialManager

NUM_CREDENTIAL_FIELDS = 2


def test_keyring_manager_init_no_keyring() -> None:
    """Test KeyringCredentialManager initialization when keyring is not available."""
    with (
        patch("evohome_cli.auth.keyring", None),
        pytest.raises(CredentialStorageError, match="keyring package is not installed"),
    ):
        KeyringCredentialManager()


def test_get_credentials_success() -> None:
    """Test retrieving stored credentials when keyring is available."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = lambda service, key: {
        "username": "testuser@example.com",
        "password": "testpass123",
    }.get(key)

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        result = manager.get_credentials()

    assert result is not None
    assert result == ("testuser@example.com", "testpass123")
    assert mock_keyring.get_password.call_count == NUM_CREDENTIAL_FIELDS


def test_get_credentials_missing_username() -> None:
    """Test retrieving credentials when username is not stored."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = lambda service, key: {
        "username": None,
        "password": "testpass123",
    }.get(key)

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        result = manager.get_credentials()

    assert result is None


def test_get_credentials_missing_password() -> None:
    """Test retrieving credentials when password is not stored."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = lambda service, key: {
        "username": "testuser@example.com",
        "password": None,
    }.get(key)

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        result = manager.get_credentials()

    assert result is None


def test_get_credentials_keyring_error() -> None:
    """Test retrieving credentials when keyring raises an error."""
    mock_keyring = MagicMock()
    mock_keyring.errors.KeyringError = Exception
    mock_keyring.get_password.side_effect = mock_keyring.errors.KeyringError(
        "Keyring error"
    )

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        with pytest.raises(
            CredentialStorageError, match="Failed to retrieve credentials"
        ):
            manager.get_credentials()


def test_store_credentials_success() -> None:
    """Test storing credentials when keyring is available."""
    mock_keyring = MagicMock()

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        manager.store_credentials("testuser@example.com", "testpass123")

    assert mock_keyring.set_password.call_count == NUM_CREDENTIAL_FIELDS
    calls = mock_keyring.set_password.call_args_list
    assert calls[0][0][1] == "username"
    assert calls[0][0][2] == "testuser@example.com"
    assert calls[1][0][1] == "password"
    assert calls[1][0][2] == "testpass123"


def test_store_credentials_keyring_error() -> None:
    """Test storing credentials when keyring raises an error."""
    mock_keyring = MagicMock()
    mock_keyring.errors.KeyringError = Exception
    mock_keyring.set_password.side_effect = mock_keyring.errors.KeyringError(
        "Storage error"
    )

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        with pytest.raises(CredentialStorageError, match="Failed to store credentials"):
            manager.store_credentials("testuser@example.com", "testpass123")


def test_delete_credentials_success() -> None:
    """Test deleting stored credentials when keyring is available."""
    mock_keyring = MagicMock()
    mock_keyring.errors.PasswordDeleteError = Exception

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        manager.delete_credentials()

    assert mock_keyring.delete_password.call_count == NUM_CREDENTIAL_FIELDS
    calls = mock_keyring.delete_password.call_args_list
    assert calls[0][0][1] == "username"
    assert calls[1][0][1] == "password"


def test_delete_credentials_not_found() -> None:
    """Test deleting credentials when they don't exist."""
    mock_keyring = MagicMock()
    mock_keyring.errors.PasswordDeleteError = Exception
    mock_keyring.delete_password.side_effect = mock_keyring.errors.PasswordDeleteError(
        "Not found"
    )

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        # Should not raise an error
        manager.delete_credentials()


def test_delete_credentials_keyring_error() -> None:
    """Test deleting credentials when keyring raises a non-PasswordDeleteError."""
    mock_keyring = MagicMock()
    mock_keyring.errors.PasswordDeleteError = type(
        "PasswordDeleteError", (Exception,), {}
    )
    mock_keyring.errors.KeyringError = type("KeyringError", (Exception,), {})

    # First delete succeeds, second fails with KeyringError
    def delete_side_effect(service: str, key: str) -> None:
        if key == "password":
            raise mock_keyring.errors.KeyringError("Backend error")

    mock_keyring.delete_password.side_effect = delete_side_effect

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        with pytest.raises(CredentialStorageError, match="Failed to delete password"):
            manager.delete_credentials()


def test_storage_location_macos() -> None:
    """Test getting storage location description for macOS."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "Keychain"
    mock_backend.__class__.__module__ = "keyring.backends.macOS"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        location = manager.storage_location

    assert "macOS Keychain" in location


def test_storage_location_windows() -> None:
    """Test getting storage location description for Windows."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "WinVaultKeyring"
    mock_backend.__class__.__module__ = "keyring.backends.Windows"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        location = manager.storage_location

    assert "Windows Credential Manager" in location


def test_storage_location_linux() -> None:
    """Test getting storage location description for Linux."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "SecretService"
    mock_backend.__class__.__module__ = "keyring.backends.SecretService"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        location = manager.storage_location

    assert "Linux Secret Service" in location


def test_storage_location_file_backend() -> None:
    """Test getting storage location description for file backend."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "PlaintextKeyring"
    mock_backend.__class__.__module__ = "keyring.backends.file"
    mock_backend.filename = "/path/to/keyring"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        location = manager.storage_location

    assert "Encrypted file" not in location
    assert "/path/to/keyring" in location


def test_storage_location_generic() -> None:
    """Test getting storage location description for generic backend."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock(spec=[])
    mock_backend.__class__.__name__ = "CustomKeyring"
    mock_backend.__class__.__module__ = "custom.backend"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        location = manager.storage_location

    assert "Keyring backend: CustomKeyring" in location


def test_storage_location_error() -> None:
    """Test getting storage location when keyring raises an error."""
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.side_effect = Exception("Backend error")

    with patch("evohome_cli.auth.keyring", mock_keyring):
        manager = KeyringCredentialManager()
        location = manager.storage_location

    assert "System credential store" in location
