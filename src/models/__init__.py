"""Pydantic models for SpecterDefence."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Tenant(BaseModel):
    """Tenant model for O365 registrations."""
    id: str
    tenant_id: str
    display_name: str
    domain: str
    status: str = "active"
    created_at: datetime
    last_synced: Optional[datetime] = None

class SecurityAlert(BaseModel):
    """Security alert model."""
    id: str
    tenant_id: str
    severity: str
    title: str
    description: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
