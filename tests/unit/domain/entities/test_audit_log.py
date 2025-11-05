"""Unit tests for AuditLog entity."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.entities.audit_log import AuditLog


class TestAuditLogCreation:
    """Test AuditLog entity creation."""

    def test_create_audit_log_with_user(self):
        """Test creating audit log with user ID."""
        log_id = uuid4()
        user_id = uuid4()
        resource_id = uuid4()
        timestamp = datetime.utcnow()

        log = AuditLog(
            id=log_id,
            user_id=user_id,
            action="CREATE",
            resource_type="account",
            resource_id=resource_id,
            details={"name": "Test Account"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            timestamp=timestamp
        )

        assert log.id == log_id
        assert log.user_id == user_id
        assert log.action == "CREATE"
        assert log.resource_type == "account"
        assert log.resource_id == resource_id
        assert log.ip_address == "192.168.1.1"
        assert log.timestamp == timestamp

    def test_create_system_audit_log(self):
        """Test creating system-generated audit log (no user)."""
        log = AuditLog(
            id=uuid4(),
            user_id=None,
            action="SYSTEM_CLEANUP",
            resource_type="cache",
            resource_id=None,
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.user_id is None
        assert log.is_system_action() is True

    def test_empty_action_raises_error(self):
        """Test empty action raises error."""
        with pytest.raises(ValueError) as exc_info:
            AuditLog(
                id=uuid4(),
                user_id=uuid4(),
                action="",
                resource_type="account",
                resource_id=uuid4(),
                details={},
                ip_address=None,
                user_agent=None,
                timestamp=datetime.utcnow()
            )
        assert "action cannot be empty" in str(exc_info.value)

    def test_empty_resource_type_raises_error(self):
        """Test empty resource_type raises error."""
        with pytest.raises(ValueError) as exc_info:
            AuditLog(
                id=uuid4(),
                user_id=uuid4(),
                action="CREATE",
                resource_type="",
                resource_id=uuid4(),
                details={},
                ip_address=None,
                user_agent=None,
                timestamp=datetime.utcnow()
            )
        assert "resource_type cannot be empty" in str(exc_info.value)

    def test_action_too_long_raises_error(self):
        """Test action exceeding max length raises error."""
        with pytest.raises(ValueError):
            AuditLog(
                id=uuid4(),
                user_id=uuid4(),
                action="x" * 101,
                resource_type="test",
                resource_id=uuid4(),
                details={},
                ip_address=None,
                user_agent=None,
                timestamp=datetime.utcnow()
            )


class TestAuditLogMethods:
    """Test AuditLog methods."""

    def test_is_user_action_true(self):
        """Test is_user_action returns True when user_id is set."""
        log = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.is_user_action() is True

    def test_is_user_action_false(self):
        """Test is_user_action returns False when user_id is None."""
        log = AuditLog(
            id=uuid4(),
            user_id=None,
            action="SYSTEM",
            resource_type="cache",
            resource_id=None,
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.is_user_action() is False

    def test_is_system_action_true(self):
        """Test is_system_action returns True when user_id is None."""
        log = AuditLog(
            id=uuid4(),
            user_id=None,
            action="SYSTEM",
            resource_type="cache",
            resource_id=None,
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.is_system_action() is True

    def test_is_system_action_false(self):
        """Test is_system_action returns False when user_id is set."""
        log = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.is_system_action() is False


class TestAuditLogDetails:
    """Test AuditLog details management."""

    def test_get_detail_existing(self):
        """Test get_detail returns value for existing key."""
        log = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={"name": "Test Account", "balance": 100.50},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.get_detail("name") == "Test Account"
        assert log.get_detail("balance") == 100.50

    def test_get_detail_nonexistent(self):
        """Test get_detail returns None for non-existent key."""
        log = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={"name": "Test"},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.get_detail("nonexistent") is None

    def test_has_detail_true(self):
        """Test has_detail returns True for existing key."""
        log = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={"name": "Test"},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.has_detail("name") is True

    def test_has_detail_false(self):
        """Test has_detail returns False for non-existent key."""
        log = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log.has_detail("name") is False


class TestAuditLogEquality:
    """Test AuditLog equality and hashing."""

    def test_logs_with_same_id_are_equal(self):
        """Test logs with same ID are equal."""
        log_id = uuid4()
        log1 = AuditLog(
            id=log_id,
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        log2 = AuditLog(
            id=log_id,
            user_id=uuid4(),
            action="DELETE",
            resource_type="user",
            resource_id=uuid4(),
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log1 == log2

    def test_logs_with_different_ids_not_equal(self):
        """Test logs with different IDs are not equal."""
        log1 = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        log2 = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        assert log1 != log2


class TestAuditLogImmutability:
    """Test AuditLog is immutable."""

    def test_cannot_change_action(self):
        """Test action cannot be changed."""
        log = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        with pytest.raises(AttributeError):
            log.action = "DELETE"  # type: ignore

    def test_cannot_change_details(self):
        """Test details dict is mutable but replacement blocked."""
        log = AuditLog(
            id=uuid4(),
            user_id=uuid4(),
            action="CREATE",
            resource_type="account",
            resource_id=uuid4(),
            details={"name": "Test"},
            ip_address=None,
            user_agent=None,
            timestamp=datetime.utcnow()
        )
        with pytest.raises(AttributeError):
            log.details = {}  # type: ignore
