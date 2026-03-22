"""Endpoint device and event models for SpecterDefence Windows Agent."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.types import JSONB, UUID


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class DeviceStatus(StrEnum):
    """Enrollment status for endpoint devices."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class EndpointEventType(StrEnum):
    """Types of events detected by the Windows agent."""

    SUSPICIOUS_PROCESS = "suspicious_process"
    POWERSHELL_ABUSE = "powershell_abuse"
    USB_INSERTION = "usb_insertion"
    CREDENTIAL_DUMP = "credential_dump"
    PERSISTENCE_MECHANISM = "persistence_mechanism"
    DEFENDER_TAMPER = "defender_tamper"
    LOCAL_ACCOUNT_CHANGE = "local_account_change"


class EndpointEventSeverity(StrEnum):
    """Severity levels for endpoint events."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EndpointDeviceModel(Base):
    """Enrolled endpoint device database model."""

    __tablename__ = "endpoint_devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
        comment="Tenant this device belongs to",
    )
    hostname: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Device hostname"
    )
    os_version: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Windows version string"
    )
    agent_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Installed agent version"
    )
    status: Mapped[DeviceStatus] = mapped_column(
        SQLEnum(DeviceStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DeviceStatus.PENDING,
        comment="Device enrollment status",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="SHA-256 hash of device auth token"
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last heartbeat timestamp"
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="Last known IP address"
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_endpoint_devices_tenant_status", "tenant_id", "status"),
        Index("ix_endpoint_devices_hostname", "hostname"),
    )

    def __repr__(self) -> str:
        return f"<EndpointDevice(id={self.id}, hostname={self.hostname}, status={self.status})>"


class EndpointEventModel(Base):
    """Raw event data from endpoint agents."""

    __tablename__ = "endpoint_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("endpoint_devices.id"),
        nullable=False,
        index=True,
        comment="Device that reported this event",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
        comment="Tenant this event belongs to",
    )
    event_type: Mapped[EndpointEventType] = mapped_column(
        SQLEnum(
            EndpointEventType,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="Type of endpoint event",
    )
    severity: Mapped[EndpointEventSeverity] = mapped_column(
        SQLEnum(
            EndpointEventSeverity,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="Event severity level",
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Short event title"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Detailed event description"
    )
    process_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Process name involved"
    )
    command_line: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Full command line captured"
    )
    user_context: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Windows user context (DOMAIN\\user)"
    )
    source_ip: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="Source IP if network-related"
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, comment="Additional event metadata"
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="When the agent detected the event"
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="When the backend received the event"
    )

    __table_args__ = (
        Index("ix_endpoint_events_device_time", "device_id", "detected_at"),
        Index("ix_endpoint_events_tenant_time", "tenant_id", "detected_at"),
        Index("ix_endpoint_events_type_severity", "event_type", "severity"),
    )

    def __repr__(self) -> str:
        return f"<EndpointEvent(id={self.id}, type={self.event_type}, severity={self.severity})>"
