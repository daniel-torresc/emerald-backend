"""
Mapper between AuditLog domain entity and AuditLogModel database model.

This mapper handles bidirectional conversion:
- to_entity(): Convert SQLAlchemy model → Domain entity
- to_model(): Convert Domain entity → SQLAlchemy model

The mapper lives in the Infrastructure layer and knows about both:
- Domain entities (app.domain.entities.audit_log.AuditLog)
- Database models (app.infrastructure...models.audit_log_model.AuditLogModel)

Note: AuditLog is immutable, so there's no update operation.
"""

from typing import Any

from app.domain.entities.audit_log import AuditLog
from app.infrastructure.adapters.outbound.persistence.postgresql.models.audit_log_model import (
    AuditLogModel,
)


class AuditLogMapper:
    """
    Mapper between AuditLog entity and AuditLogModel.

    Handles conversion between:
    - Pure domain entity (AuditLog) - immutable
    - SQLAlchemy ORM model (AuditLogModel)

    Note: AuditLog is immutable, so only to_model() for INSERT operations.
    No UPDATE operations allowed on audit logs.
    """

    @staticmethod
    def to_entity(model: AuditLogModel) -> AuditLog:
        """
        Convert SQLAlchemy model to domain entity.

        Args:
            model: AuditLogModel from database

        Returns:
            AuditLog domain entity

        Example:
            audit_model = session.get(AuditLogModel, audit_id)
            audit_entity = AuditLogMapper.to_entity(audit_model)
        """
        # Combine old_values, new_values, and extra_metadata into details dict
        details: dict[str, str | int | float | bool | None] = {}

        if model.old_values:
            for key, value in model.old_values.items():
                details[f"old_{key}"] = value

        if model.new_values:
            for key, value in model.new_values.items():
                details[f"new_{key}"] = value

        if model.extra_metadata:
            details.update(model.extra_metadata)

        # Add status and error if present
        if model.status:
            details["status"] = model.status.value

        if model.error_message:
            details["error_message"] = model.error_message

        return AuditLog(
            id=model.id,
            user_id=model.user_id,
            action=model.action.value,
            resource_type=model.entity_type,
            resource_id=model.entity_id,
            details=details,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
            timestamp=model.created_at,
        )

    @staticmethod
    def to_model(entity: AuditLog) -> AuditLogModel:
        """
        Convert domain entity to SQLAlchemy model.

        Args:
            entity: AuditLog domain entity

        Returns:
            AuditLogModel for database persistence

        Note: AuditLog is immutable, so this only supports INSERT operations.
        There's no existing_model parameter because audit logs cannot be updated.

        Example:
            audit_entity = AuditLog(...)
            audit_model = AuditLogMapper.to_model(audit_entity)
            session.add(audit_model)
        """
        from app.infrastructure.adapters.outbound.persistence.postgresql.models.enums import (
            AuditAction,
            AuditStatus,
        )

        # Try to convert action string to AuditAction enum
        try:
            action_enum = AuditAction(entity.action)
        except ValueError:
            # If action doesn't match enum, use CREATE as default
            action_enum = AuditAction.CREATE

        # Extract old/new values from details
        old_values: dict[str, Any] = {}
        new_values: dict[str, Any] = {}
        extra_metadata: dict[str, Any] = {}

        for key, value in entity.details.items():
            if key.startswith("old_"):
                old_values[key[4:]] = value  # Remove "old_" prefix
            elif key.startswith("new_"):
                new_values[key[4:]] = value  # Remove "new_" prefix
            elif key not in ("status", "error_message"):
                extra_metadata[key] = value

        # Extract status and error
        status = AuditStatus.SUCCESS
        if "status" in entity.details:
            try:
                status = AuditStatus(str(entity.details["status"]))
            except ValueError:
                status = AuditStatus.SUCCESS

        error_message = entity.details.get("error_message")

        return AuditLogModel(
            id=entity.id,
            user_id=entity.user_id,
            action=action_enum,
            entity_type=entity.resource_type,
            entity_id=entity.resource_id,
            old_values=old_values if old_values else None,
            new_values=new_values if new_values else None,
            description=None,  # Not in domain entity
            ip_address=entity.ip_address,
            user_agent=entity.user_agent,
            request_id=None,  # Not in domain entity
            status=status,
            error_message=str(error_message) if error_message else None,
            extra_metadata=extra_metadata if extra_metadata else None,
            created_at=entity.timestamp,
        )
