"""Unit tests for AccountShare entity."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.account_share import AccountShare
from app.domain.value_objects.permission import Permission


class TestAccountShareCreation:
    """Test AccountShare entity creation."""

    def test_create_account_share_minimal(self):
        """Test creating account share with minimal data."""
        share_id = uuid4()
        account_id = uuid4()
        owner_id = uuid4()
        recipient_id = uuid4()

        share = AccountShare(
            id=share_id,
            account_id=account_id,
            shared_by_user_id=owner_id,
            shared_with_user_id=recipient_id,
            permissions=[Permission.ACCOUNT_READ]
        )

        assert share.id == share_id
        assert share.account_id == account_id
        assert share.shared_by_user_id == owner_id
        assert share.shared_with_user_id == recipient_id
        assert share.can_view is True
        assert share.can_edit is False
        assert share.can_delete is False
        assert share.expires_at is None

    def test_share_with_self_raises_error(self):
        """Test sharing with self raises error."""
        user_id = uuid4()
        with pytest.raises(ValueError) as exc_info:
            AccountShare(
                id=uuid4(),
                account_id=uuid4(),
                shared_by_user_id=user_id,
                shared_with_user_id=user_id,
                permissions=[Permission.ACCOUNT_READ]
            )
        assert "Cannot share account with yourself" in str(exc_info.value)


class TestAccountShareStatus:
    """Test AccountShare status methods."""

    def test_is_active_true(self):
        """Test is_active returns True for active share."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        assert share.is_active() is True

    def test_is_active_false_when_revoked(self):
        """Test is_active returns False when revoked."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            revoked_at=datetime.utcnow()
        )
        assert share.is_active() is False

    def test_is_active_false_when_expired(self):
        """Test is_active returns False when expired."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        assert share.is_active() is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired share."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert share.is_expired() is True

    def test_is_expired_false_when_no_expiration(self):
        """Test is_expired returns False when no expiration set."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )
        assert share.is_expired() is False

    def test_is_revoked_true(self):
        """Test is_revoked returns True when revoked."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            revoked_at=datetime.utcnow()
        )
        assert share.is_revoked() is True

    def test_is_revoked_false(self):
        """Test is_revoked returns False when not revoked."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )
        assert share.is_revoked() is False


class TestAccountShareRevoke:
    """Test AccountShare revoke functionality."""

    def test_revoke_share(self):
        """Test revoking an active share."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )
        share.revoke()
        assert share.revoked_at is not None
        assert share.is_revoked() is True

    def test_revoke_already_revoked_raises_error(self):
        """Test revoking already revoked share raises error."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            revoked_at=datetime.utcnow()
        )
        with pytest.raises(ValueError) as exc_info:
            share.revoke()
        assert "already revoked" in str(exc_info.value)


class TestAccountSharePermissions:
    """Test AccountShare permission management."""

    def test_has_permission_true_when_active(self):
        """Test has_permission returns True for active share."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )
        assert share.has_permission(Permission.ACCOUNT_READ) is True

    def test_has_permission_false_when_not_granted(self):
        """Test has_permission returns False when permission not granted."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )
        assert share.has_permission(Permission.ACCOUNT_WRITE) is False

    def test_has_permission_false_when_inactive(self):
        """Test has_permission returns False for inactive share."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            revoked_at=datetime.utcnow()
        )
        assert share.has_permission(Permission.ACCOUNT_READ) is False

    def test_grant_permission(self):
        """Test granting permission to share."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )
        share.grant_permission(Permission.ACCOUNT_WRITE)
        assert Permission.ACCOUNT_WRITE in share.permissions

    def test_revoke_permission(self):
        """Test revoking permission from share."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ, Permission.ACCOUNT_WRITE]
        )
        share.revoke_permission(Permission.ACCOUNT_WRITE)
        assert Permission.ACCOUNT_WRITE not in share.permissions


class TestAccountShareExpiration:
    """Test AccountShare expiration management."""

    def test_extend_expiration(self):
        """Test extending expiration date."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        new_expiration = datetime.utcnow() + timedelta(days=7)
        share.extend_expiration(new_expiration)
        assert share.expires_at == new_expiration

    def test_extend_expiration_to_past_raises_error(self):
        """Test extending to past date raises error."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )
        with pytest.raises(ValueError) as exc_info:
            share.extend_expiration(datetime.utcnow() - timedelta(days=1))
        assert "in the past" in str(exc_info.value)

    def test_reduce_expiration_raises_error(self):
        """Test reducing expiration raises error."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        with pytest.raises(ValueError) as exc_info:
            share.extend_expiration(datetime.utcnow() + timedelta(days=3))
        assert "reduce expiration" in str(exc_info.value)

    def test_make_permanent(self):
        """Test making share permanent."""
        share = AccountShare(
            id=uuid4(),
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        share.make_permanent()
        assert share.expires_at is None
        assert share.is_expired() is False


class TestAccountShareEquality:
    """Test AccountShare equality."""

    def test_shares_with_same_id_are_equal(self):
        """Test shares with same ID are equal."""
        share_id = uuid4()
        share1 = AccountShare(
            id=share_id,
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )
        share2 = AccountShare(
            id=share_id,
            account_id=uuid4(),
            shared_by_user_id=uuid4(),
            shared_with_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_WRITE]
        )
        assert share1 == share2
