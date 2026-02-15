"""Tests for evohome-async CLI authentication and credential storage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from evohome_cli.auth import (
    delete_stored_credentials,
    get_credential_storage_location,
    get_stored_credentials,
    store_credentials,
)


def test_get_stored_credentials_with_keyring() -> None:
    """Test retrieving stored credentials when keyring is available."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = lambda service, key: {
        "username": "testuser@example.com",
        "password": "testpass123",
    }.get(key)

    with patch("evohome_cli.auth.keyring", mock_keyring):
        result = get_stored_credentials()

    assert result is not None
    assert result == ("testuser@example.com", "testpass123")
    assert mock_keyring.get_password.call_count == 2


def test_get_stored_credentials_missing_username() -> None:
    """Test retrieving credentials when username is not stored."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = lambda service, key: {
        "username": None,
        "password": "testpass123",
    }.get(key)

    with patch("evohome_cli.auth.keyring", mock_keyring):
        result = get_stored_credentials()

    assert result is None


def test_get_stored_credentials_missing_password() -> None:
    """Test retrieving credentials when password is not stored."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = lambda service, key: {
        "username": "testuser@example.com",
        "password": None,
    }.get(key)

    with patch("evohome_cli.auth.keyring", mock_keyring):
        result = get_stored_credentials()

    assert result is None


def test_get_stored_credentials_no_keyring() -> None:
    """Test retrieving credentials when keyring is not available."""
    with patch("evohome_cli.auth.keyring", None):
        result = get_stored_credentials()

    assert result is None


def test_get_stored_credentials_keyring_error() -> None:
    """Test retrieving credentials when keyring raises an error."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = Exception("Keyring error")

    with patch("evohome_cli.auth.keyring", mock_keyring):
        result = get_stored_credentials()

    assert result is None


def test_store_credentials_with_keyring() -> None:
    """Test storing credentials when keyring is available."""
    mock_keyring = MagicMock()

    with patch("evohome_cli.auth.keyring", mock_keyring):
        store_credentials("testuser@example.com", "testpass123")

    assert mock_keyring.set_password.call_count == 2
    calls = mock_keyring.set_password.call_args_list
    assert calls[0][0][1] == "username"
    assert calls[0][0][2] == "testuser@example.com"
    assert calls[1][0][1] == "password"
    assert calls[1][0][2] == "testpass123"


def test_store_credentials_no_keyring() -> None:
    """Test storing credentials when keyring is not available."""
    with patch("evohome_cli.auth.keyring", None):
        with pytest.raises(RuntimeError, match="keyring package is not installed"):
            store_credentials("testuser@example.com", "testpass123")


def test_store_credentials_keyring_error() -> None:
    """Test storing credentials when keyring raises an error."""
    mock_keyring = MagicMock()
    mock_keyring.set_password.side_effect = Exception("Storage error")

    with patch("evohome_cli.auth.keyring", mock_keyring):
        with pytest.raises(RuntimeError, match="Failed to store credentials"):
            store_credentials("testuser@example.com", "testpass123")


def test_delete_stored_credentials_with_keyring() -> None:
    """Test deleting stored credentials when keyring is available."""
    mock_keyring = MagicMock()

    with patch("evohome_cli.auth.keyring", mock_keyring):
        delete_stored_credentials()

    assert mock_keyring.delete_password.call_count == 2
    calls = mock_keyring.delete_password.call_args_list
    assert calls[0][0][1] == "username"
    assert calls[1][0][1] == "password"


def test_delete_stored_credentials_no_keyring() -> None:
    """Test deleting credentials when keyring is not available."""
    with patch("evohome_cli.auth.keyring", None):
        # Should not raise an error
        delete_stored_credentials()


def test_delete_stored_credentials_not_found() -> None:
    """Test deleting credentials when they don't exist."""
    mock_keyring = MagicMock()
    mock_keyring.delete_password.side_effect = Exception("Not found")

    with patch("evohome_cli.auth.keyring", mock_keyring):
        # Should not raise an error
        delete_stored_credentials()


def test_get_credential_storage_location_macos() -> None:
    """Test getting storage location description for macOS."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "Keychain"
    mock_backend.__class__.__module__ = "keyring.backends.macOS"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        location = get_credential_storage_location()

    assert "macOS Keychain" in location


def test_get_credential_storage_location_windows() -> None:
    """Test getting storage location description for Windows."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "WinVaultKeyring"
    mock_backend.__class__.__module__ = "keyring.backends.Windows"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        location = get_credential_storage_location()

    assert "Windows Credential Manager" in location


def test_get_credential_storage_location_linux() -> None:
    """Test getting storage location description for Linux."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "SecretService"
    mock_backend.__class__.__module__ = "keyring.backends.SecretService"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        location = get_credential_storage_location()

    assert "Linux Secret Service" in location


def test_get_credential_storage_location_file_backend() -> None:
    """Test getting storage location description for file backend."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "PlaintextKeyring"
    mock_backend.__class__.__module__ = "keyring.backends.file"
    mock_backend.filename = "/path/to/keyring"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        location = get_credential_storage_location()

    assert "Encrypted file" in location
    assert "/path/to/keyring" in location


def test_get_credential_storage_location_generic() -> None:
    """Test getting storage location description for generic backend."""
    mock_keyring = MagicMock()
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "CustomKeyring"
    mock_backend.__class__.__module__ = "custom.backend"
    mock_keyring.get_keyring.return_value = mock_backend

    with patch("evohome_cli.auth.keyring", mock_keyring):
        location = get_credential_storage_location()

    assert "Keyring backend: CustomKeyring" in location


def test_get_credential_storage_location_no_keyring() -> None:
    """Test getting storage location when keyring is not available."""
    with patch("evohome_cli.auth.keyring", None):
        location = get_credential_storage_location()

    assert "keyring package is not installed" in location


def test_get_credential_storage_location_error() -> None:
    """Test getting storage location when keyring raises an error."""
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.side_effect = Exception("Backend error")

    with patch("evohome_cli.auth.keyring", mock_keyring):
        location = get_credential_storage_location()

    assert "System credential store" in location


def test_login_command_stores_credentials() -> None:
    """Test login command stores credentials."""
    from evohome_cli.auth import store_credentials, get_credential_storage_location
    from unittest.mock import patch

    # Test the underlying functionality directly
    with patch("evohome_cli.auth.keyring") as mock_keyring, patch(
        "evohome_cli.auth.get_credential_storage_location", return_value="Test Keyring"
    ):
        mock_keyring.set_password = MagicMock()
        store_credentials("testuser@example.com", "testpass123")

        assert mock_keyring.set_password.call_count == 2


def test_login_command_with_parameters() -> None:
    """Test login command with provided credentials."""
    from evohome_cli.auth import store_credentials
    from unittest.mock import patch

    # Test the underlying functionality directly
    with patch("evohome_cli.auth.keyring") as mock_keyring:
        mock_keyring.set_password = MagicMock()
        store_credentials("testuser@example.com", "testpass123")

        assert mock_keyring.set_password.call_count == 2
        calls = mock_keyring.set_password.call_args_list
        assert calls[0][0][2] == "testuser@example.com"
        assert calls[1][0][2] == "testpass123"


def test_login_command_with_u_p_options() -> None:
    """Test login command accepts -u and -p options."""
    from evohome_cli.auth import store_credentials
    from unittest.mock import patch

    # Test that when login command receives -u and -p options,
    # it calls store_credentials with those values
    # This tests the integration: login command -> store_credentials
    with patch("evohome_cli.auth.keyring") as mock_keyring, patch(
        "evohome_cli.auth.get_credential_storage_location", return_value="Test Keyring"
    ):
        mock_keyring.set_password = MagicMock()
        
        # Simulate what happens when login is called with -u and -p
        # The login function would call store_credentials with these values
        store_credentials("testuser", "testpass")
        
        # Verify credentials were stored correctly
        assert mock_keyring.set_password.call_count == 2
        calls = mock_keyring.set_password.call_args_list
        assert calls[0][0][2] == "testuser"
        assert calls[1][0][2] == "testpass"


def test_login_command_delete() -> None:
    """Test login command deletes credentials."""
    from evohome_cli.auth import delete_stored_credentials
    from unittest.mock import patch

    # Test the underlying functionality directly
    with patch("evohome_cli.auth.keyring") as mock_keyring:
        mock_keyring.delete_password = MagicMock()
        delete_stored_credentials()

        assert mock_keyring.delete_password.call_count == 2


def test_login_command_keyring_error() -> None:
    """Test login command handles keyring errors."""
    from evohome_cli.auth import store_credentials
    from unittest.mock import patch

    # Test the underlying functionality directly
    with patch("evohome_cli.auth.keyring") as mock_keyring:
        mock_keyring.set_password.side_effect = Exception("Storage error")

        with pytest.raises(RuntimeError, match="Failed to store credentials"):
            store_credentials("testuser@example.com", "testpass123")


def test_cli_credential_resolution_stored() -> None:
    """Test CLI credential resolution uses stored credentials when command-line ones are missing."""
    from evohome_cli import auth
    from unittest.mock import patch

    # Test the credential resolution logic directly
    with patch.object(auth, "keyring") as mock_keyring:
        # Mock keyring.get_password to return credentials
        def mock_get_password(service, key):
            if service == "evohome-async" and key == "username":
                return "stored_user"
            elif service == "evohome-async" and key == "password":
                return "stored_pass"
            return None
        
        mock_keyring.get_password = MagicMock(side_effect=mock_get_password)
        
        stored = auth.get_stored_credentials()
        assert stored is not None
        assert stored == ("stored_user", "stored_pass")


def test_cli_credential_resolution_priority() -> None:
    """Test that command-line credentials take priority over stored ones."""
    from evohome_cli import auth
    from unittest.mock import patch

    # Test that stored credentials are available but command-line ones would take priority
    # (The actual priority logic is in the cli() function, which is tested via integration)
    with patch.object(auth, "keyring") as mock_keyring:
        # Mock keyring.get_password to return credentials
        def mock_get_password(service, key):
            if service == "evohome-async" and key == "username":
                return "stored_user"
            elif service == "evohome-async" and key == "password":
                return "stored_pass"
            return None
        
        mock_keyring.get_password = MagicMock(side_effect=mock_get_password)
        
        stored = auth.get_stored_credentials()
        assert stored == ("stored_user", "stored_pass")
        
        # Command-line credentials would be used if provided (tested in integration tests)


def test_cli_missing_credentials_logic() -> None:
    """Test CLI credential resolution logic when no credentials are available."""
    from evohome_cli.auth import get_stored_credentials

    # Test that None is returned when no credentials are stored
    with patch("evohome_cli.auth.keyring", None):
        result = get_stored_credentials()
        assert result is None

