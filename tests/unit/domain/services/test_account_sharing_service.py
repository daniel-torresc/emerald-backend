"""Unit tests for AccountSharingService domain service."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.account import Account
from app.domain.entities.user import User
from app.domain.exceptions import AccountShareError
from app.domain.services.account_sharing_service import AccountSharingService
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.email import Email
from app.domain.value_objects.money import Money
from app.domain.value_objects.password_hash import PasswordHash
from app.domain.value_objects.permission import Permission
from app.domain.value_objects.username import Username


class TestCreateAccountShare:
    """Test creating account shares."""

    def test_create_account_share_success(self):
        """Test creating valid account share."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner User"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test Account",
            description=None,
            balance=Money(amount=100, currency=Currency.USD)
        )
        recipient_id = uuid4()

        share = AccountSharingService.create_account_share(
            account=account,
            sharing_user=owner,
            recipient_user_id=recipient_id,
            permissions=[Permission.ACCOUNT_READ],
            can_view=True,
            can_edit=False
        )

        assert share.account_id == account.id
        assert share.shared_by_user_id == owner.id
        assert share.shared_with_user_id == recipient_id
        assert share.can_view is True
        assert share.can_edit is False
        assert recipient_id in account.shared_with_user_ids

    def test_create_share_non_owner_raises_error(self):
        """Test creating share by non-owner raises error."""
        non_owner = User(
            id=uuid4(),
            email=Email("user@example.com"),
            username=Username("user"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="User"
        )
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )

        with pytest.raises(AccountShareError) as exc_info:
            AccountSharingService.create_account_share(
                account=account,
                sharing_user=non_owner,
                recipient_user_id=uuid4(),
                permissions=[Permission.ACCOUNT_READ]
            )
        assert "owner" in str(exc_info.value)

    def test_create_share_with_self_raises_error(self):
        """Test sharing with self raises error."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )

        with pytest.raises(AccountShareError) as exc_info:
            AccountSharingService.create_account_share(
                account=account,
                sharing_user=owner,
                recipient_user_id=user_id,
                permissions=[Permission.ACCOUNT_READ]
            )
        assert "yourself" in str(exc_info.value)

    def test_create_share_already_shared_raises_error(self):
        """Test sharing already shared account raises error."""
        user_id = uuid4()
        recipient_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            shared_with_user_ids=[recipient_id]
        )

        with pytest.raises(AccountShareError) as exc_info:
            AccountSharingService.create_account_share(
                account=account,
                sharing_user=owner,
                recipient_user_id=recipient_id,
                permissions=[Permission.ACCOUNT_READ]
            )
        assert "already shared" in str(exc_info.value)

    def test_create_share_expiration_in_past_raises_error(self):
        """Test creating share with past expiration raises error."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )

        with pytest.raises(AccountShareError) as exc_info:
            AccountSharingService.create_account_share(
                account=account,
                sharing_user=owner,
                recipient_user_id=uuid4(),
                permissions=[Permission.ACCOUNT_READ],
                expires_at=datetime.utcnow() - timedelta(days=1)
            )
        assert "future" in str(exc_info.value)

    def test_create_share_no_permissions_raises_error(self):
        """Test creating share without any permissions raises error."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )

        with pytest.raises(AccountShareError) as exc_info:
            AccountSharingService.create_account_share(
                account=account,
                sharing_user=owner,
                recipient_user_id=uuid4(),
                permissions=[],
                can_view=False,
                can_edit=False,
                can_delete=False
            )
        assert "at least one permission" in str(exc_info.value)


class TestRevokeAccountShare:
    """Test revoking account shares."""

    def test_revoke_share_success(self):
        """Test revoking share successfully."""
        user_id = uuid4()
        recipient_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        share = AccountSharingService.create_account_share(
            account=account,
            sharing_user=owner,
            recipient_user_id=recipient_id,
            permissions=[Permission.ACCOUNT_READ]
        )

        # Verify share was created
        assert recipient_id in account.shared_with_user_ids

        AccountSharingService.revoke_account_share(share, account, owner)

        assert share.is_revoked() is True
        assert recipient_id not in account.shared_with_user_ids

    def test_revoke_share_non_owner_raises_error(self):
        """Test revoking share by non-owner raises error."""
        user_id = uuid4()
        recipient_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        non_owner = User(
            id=uuid4(),
            email=Email("user@example.com"),
            username=Username("user"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="User"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        share = AccountSharingService.create_account_share(
            account=account,
            sharing_user=owner,
            recipient_user_id=recipient_id,
            permissions=[Permission.ACCOUNT_READ]
        )

        with pytest.raises(AccountShareError):
            AccountSharingService.revoke_account_share(share, account, non_owner)


class TestUpdateSharePermissions:
    """Test updating share permissions."""

    def test_update_permissions_success(self):
        """Test updating share permissions successfully."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        share = AccountSharingService.create_account_share(
            account=account,
            sharing_user=owner,
            recipient_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            can_edit=False
        )

        AccountSharingService.update_share_permissions(
            account_share=share,
            account=account,
            updating_user=owner,
            new_permissions=[Permission.ACCOUNT_READ, Permission.ACCOUNT_WRITE],
            can_edit=True
        )

        assert share.can_edit is True
        assert Permission.ACCOUNT_WRITE in share.permissions

    def test_update_permissions_remove_all_raises_error(self):
        """Test removing all permissions raises error."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        share = AccountSharingService.create_account_share(
            account=account,
            sharing_user=owner,
            recipient_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )

        with pytest.raises(AccountShareError):
            AccountSharingService.update_share_permissions(
                account_share=share,
                account=account,
                updating_user=owner,
                new_permissions=[],
                can_view=False,
                can_edit=False,
                can_delete=False
            )


class TestExtendShareExpiration:
    """Test extending share expiration."""

    def test_extend_expiration_success(self):
        """Test extending expiration successfully."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        share = AccountSharingService.create_account_share(
            account=account,
            sharing_user=owner,
            recipient_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ],
            expires_at=datetime.utcnow() + timedelta(days=1)
        )

        new_expiration = datetime.utcnow() + timedelta(days=7)
        AccountSharingService.extend_share_expiration(
            account_share=share,
            account=account,
            extending_user=owner,
            new_expiration=new_expiration
        )

        assert share.expires_at == new_expiration


class TestValidateShareAccess:
    """Test validating share access."""

    def test_validate_share_access_true(self):
        """Test validate returns True for active share with permission."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        share = AccountSharingService.create_account_share(
            account=account,
            sharing_user=owner,
            recipient_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )

        assert AccountSharingService.validate_share_access(
            share,
            Permission.ACCOUNT_READ
        ) is True

    def test_validate_share_access_false_missing_permission(self):
        """Test validate returns False for missing permission."""
        user_id = uuid4()
        owner = User(
            id=user_id,
            email=Email("owner@example.com"),
            username=Username("owner"),
            password_hash=PasswordHash("$2b$12$" + "x" * 50),
            full_name="Owner"
        )
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        share = AccountSharingService.create_account_share(
            account=account,
            sharing_user=owner,
            recipient_user_id=uuid4(),
            permissions=[Permission.ACCOUNT_READ]
        )

        assert AccountSharingService.validate_share_access(
            share,
            Permission.ACCOUNT_WRITE
        ) is False
