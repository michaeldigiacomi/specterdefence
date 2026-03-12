"""Database models for website, SSL, and domain monitoring."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import String, Integer, Boolean, DateTime, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base


class WebsiteMonitorModel(Base):
    """Website availability monitoring."""

    __tablename__ = "website_monitors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False, comment="Internal tenant UUID"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Website name")
    url: Mapped[str] = mapped_column(String(500), nullable=False, comment="Website URL")
    
    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    check_interval_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    
    # Last check results
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="up, down, error")
    last_response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # History
    uptime_percentage: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    total_checks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_checks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SslCertificateModel(Base):
    """SSL certificate monitoring."""

    __tablename__ = "ssl_certificates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False, comment="Internal tenant UUID"
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="Domain name")
    port: Mapped[int] = mapped_column(Integer, default=443, nullable=False)
    
    # Certificate details
    issuer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    days_until_expiry: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    signature_algorithm: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Status
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_errors: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Last check
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DomainExpiryModel(Base):
    """Domain expiry monitoring."""

    __tablename__ = "domain_expiry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False, comment="Internal tenant UUID"
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="Domain name")
    
    # Registration details (from WHOIS)
    registrar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    registration_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    days_until_expiry: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whois_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Last check
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
