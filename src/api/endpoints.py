"""Agent API endpoints for SpecterDefence Windows Agent enrollment and telemetry."""

import hashlib
import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth_local import get_authorized_tenant, get_current_user
from src.database import get_db
from src.models.endpoint import (
    DeviceStatus,
    EndpointDeviceModel,
    EndpointEventModel,
    EndpointEventSeverity,
    EndpointEventType,
)

router = APIRouter()


# ============== Pydantic Request/Response Models ==============


class EnrollRequest(BaseModel):
    """Request to enroll a new endpoint device."""

    hostname: str = Field(..., min_length=1, max_length=255, description="Device hostname")
    os_version: str | None = Field(None, max_length=255, description="Windows version string")
    agent_version: str | None = Field(None, max_length=50, description="Agent version")
    enrollment_token: str = Field(..., min_length=10, description="Tenant enrollment token")


class EnrollResponse(BaseModel):
    """Response after successful enrollment."""

    device_id: uuid.UUID
    device_token: str = Field(..., description="Bearer token for this device")
    message: str


class HeartbeatRequest(BaseModel):
    """Heartbeat payload from an enrolled device."""

    agent_version: str | None = None
    os_version: str | None = None


class HeartbeatResponse(BaseModel):
    """Response to a heartbeat."""

    status: str
    message: str


class EndpointEventCreate(BaseModel):
    """A single event reported by the agent."""

    event_type: str = Field(..., description="Type of endpoint event")
    severity: str = Field(..., description="Event severity (LOW, MEDIUM, HIGH, CRITICAL)")
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    process_name: str | None = Field(None, max_length=255)
    command_line: str | None = None
    user_context: str | None = Field(None, max_length=255)
    source_ip: str | None = Field(None, max_length=45)
    metadata: dict | None = None
    detected_at: str = Field(..., description="ISO 8601 timestamp when agent detected the event")


class EventBatchRequest(BaseModel):
    """Batch of events uploaded by the agent."""

    events: list[EndpointEventCreate] = Field(..., min_length=1, max_length=500)


class EventBatchResponse(BaseModel):
    """Response after processing event batch."""

    accepted: int
    rejected: int
    message: str


class DeviceResponse(BaseModel):
    """Enrolled device visible in the dashboard."""

    id: uuid.UUID
    hostname: str
    os_version: str | None
    agent_version: str | None
    status: str
    last_heartbeat: str | None
    ip_address: str | None
    enrolled_at: str
    event_count: int = 0

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """Paginated list of devices."""

    items: list[DeviceResponse]
    total: int


class EndpointEventResponse(BaseModel):
    """Event visible in the dashboard."""

    id: uuid.UUID
    device_id: uuid.UUID
    hostname: str | None = None
    event_type: str
    severity: str
    title: str
    description: str | None
    process_name: str | None
    command_line: str | None
    user_context: str | None
    source_ip: str | None
    metadata: dict
    detected_at: str
    received_at: str

    class Config:
        from_attributes = True


class EndpointEventListResponse(BaseModel):
    """Paginated list of endpoint events."""

    items: list[EndpointEventResponse]
    total: int


class EndpointSummary(BaseModel):
    """Summary stats for the endpoints dashboard."""

    total_devices: int
    active_devices: int
    total_events_24h: int
    critical_events_24h: int
    high_events_24h: int


class GenerateTokenResponse(BaseModel):
    """Response when generating a new enrollment token."""

    enrollment_token: str
    message: str


# ============== Helper Functions ==============


def _hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


async def _get_device_by_token(db: AsyncSession, token: str) -> EndpointDeviceModel | None:
    """Look up a device by its bearer token."""
    token_hash = _hash_token(token)
    result = await db.execute(
        select(EndpointDeviceModel).where(
            EndpointDeviceModel.token_hash == token_hash,
            EndpointDeviceModel.status == DeviceStatus.ACTIVE,
        )
    )
    return result.scalar_one_or_none()


def _extract_device_token(request: Request) -> str:
    """Extract the device token from the X-Device-Token header."""
    token = request.headers.get("X-Device-Token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Device-Token header",
        )
    return token


# ============== Agent Endpoints (device-authenticated) ==============


@router.post(
    "/enroll",
    response_model=EnrollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a new endpoint device",
)
async def enroll_device(
    body: EnrollRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EnrollResponse:
    """Register a new Windows endpoint with the platform.

    The enrollment_token must match a token generated from the Settings page.
    """
    from src.models.settings import ApiKeyModel

    # Validate enrollment token against API keys with 'enrollment' scope
    result = await db.execute(
        select(ApiKeyModel).where(
            ApiKeyModel.is_active == True,  # noqa: E712
        )
    )
    api_keys = result.scalars().all()

    valid_key = None
    for key in api_keys:
        if _hash_token(body.enrollment_token) == key.key_hash:
            valid_key = key
            break

    if not valid_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid enrollment token",
        )

    # Generate a unique device token
    device_token = secrets.token_urlsafe(48)

    # Create the device record
    device = EndpointDeviceModel(
        tenant_id=valid_key.tenant_id,
        hostname=body.hostname,
        os_version=body.os_version,
        agent_version=body.agent_version,
        status=DeviceStatus.ACTIVE,
        token_hash=_hash_token(device_token),
        ip_address=request.client.host if request.client else None,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    return EnrollResponse(
        device_id=device.id,
        device_token=device_token,
        message=f"Device '{body.hostname}' enrolled successfully",
    )


@router.post(
    "/heartbeat",
    response_model=HeartbeatResponse,
    summary="Device heartbeat check-in",
)
async def device_heartbeat(
    body: HeartbeatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HeartbeatResponse:
    """Update device health status."""
    token = _extract_device_token(request)
    device = await _get_device_by_token(db, token)

    if not device:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")

    device.last_heartbeat = datetime.utcnow()
    device.ip_address = request.client.host if request.client else device.ip_address
    if body.agent_version:
        device.agent_version = body.agent_version
    if body.os_version:
        device.os_version = body.os_version

    await db.commit()

    return HeartbeatResponse(status="ok", message="Heartbeat recorded")


@router.post(
    "/events",
    response_model=EventBatchResponse,
    summary="Upload a batch of detected events",
)
async def upload_events(
    body: EventBatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EventBatchResponse:
    """Accept a batch of endpoint events from the Windows agent."""
    token = _extract_device_token(request)
    device = await _get_device_by_token(db, token)

    if not device:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")

    accepted = 0
    rejected = 0

    for evt in body.events:
        try:
            event_type = EndpointEventType(evt.event_type)
            severity = EndpointEventSeverity(evt.severity.upper())
            detected_at = datetime.fromisoformat(evt.detected_at)
        except (ValueError, KeyError):
            rejected += 1
            continue

        event = EndpointEventModel(
            device_id=device.id,
            tenant_id=device.tenant_id,
            event_type=event_type,
            severity=severity,
            title=evt.title,
            description=evt.description,
            process_name=evt.process_name,
            command_line=evt.command_line,
            user_context=evt.user_context,
            source_ip=evt.source_ip,
            event_metadata=evt.metadata or {},
            detected_at=detected_at,
        )
        db.add(event)
        accepted += 1

    await db.commit()

    return EventBatchResponse(
        accepted=accepted,
        rejected=rejected,
        message=f"Processed {accepted + rejected} events",
    )


# ============== Dashboard Endpoints (user-authenticated) ==============


@router.get(
    "/devices",
    response_model=DeviceListResponse,
    summary="List enrolled endpoint devices",
)
async def list_devices(
    tenant_id: str | list[str] | None = Depends(get_authorized_tenant),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> DeviceListResponse:
    """List enrolled endpoint devices for the dashboard."""
    query = select(EndpointDeviceModel)

    if tenant_id and tenant_id != "NONE":
        if isinstance(tenant_id, list):
            query = query.where(EndpointDeviceModel.tenant_id.in_([uuid.UUID(t) for t in tenant_id]))
        else:
            query = query.where(EndpointDeviceModel.tenant_id == uuid.UUID(tenant_id))

    if status_filter:
        try:
            query = query.where(EndpointDeviceModel.status == DeviceStatus(status_filter))
        except ValueError:
            pass

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get page
    query = query.order_by(EndpointDeviceModel.last_heartbeat.desc().nullslast())
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    devices = result.scalars().all()

    # Get event counts per device
    items = []
    for dev in devices:
        count_result = await db.execute(
            select(func.count()).where(EndpointEventModel.device_id == dev.id)
        )
        event_count = count_result.scalar() or 0

        items.append(
            DeviceResponse(
                id=dev.id,
                hostname=dev.hostname,
                os_version=dev.os_version,
                agent_version=dev.agent_version,
                status=dev.status.value,
                last_heartbeat=dev.last_heartbeat.isoformat() if dev.last_heartbeat else None,
                ip_address=dev.ip_address,
                enrolled_at=dev.enrolled_at.isoformat(),
                event_count=event_count,
            )
        )

    return DeviceListResponse(items=items, total=total)


@router.get(
    "/devices/{device_id}/events",
    response_model=EndpointEventListResponse,
    summary="Get events for a specific device",
)
async def get_device_events(
    device_id: uuid.UUID,
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> EndpointEventListResponse:
    """Get endpoint events for a specific device."""
    # Get device to verify it exists and get hostname
    dev_result = await db.execute(
        select(EndpointDeviceModel).where(EndpointDeviceModel.id == device_id)
    )
    device = dev_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    query = select(EndpointEventModel).where(EndpointEventModel.device_id == device_id)

    if event_type:
        try:
            query = query.where(EndpointEventModel.event_type == EndpointEventType(event_type))
        except ValueError:
            pass

    if severity:
        try:
            query = query.where(EndpointEventModel.severity == EndpointEventSeverity(severity.upper()))
        except ValueError:
            pass

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(EndpointEventModel.detected_at.desc())
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    events = result.scalars().all()

    items = [
        EndpointEventResponse(
            id=e.id,
            device_id=e.device_id,
            hostname=device.hostname,
            event_type=e.event_type.value,
            severity=e.severity.value,
            title=e.title,
            description=e.description,
            process_name=e.process_name,
            command_line=e.command_line,
            user_context=e.user_context,
            source_ip=e.source_ip,
            metadata=e.event_metadata,
            detected_at=e.detected_at.isoformat(),
            received_at=e.received_at.isoformat(),
        )
        for e in events
    ]

    return EndpointEventListResponse(items=items, total=total)


@router.get(
    "/events",
    response_model=EndpointEventListResponse,
    summary="Get all endpoint events across devices",
)
async def get_all_events(
    tenant_id: str | list[str] | None = Depends(get_authorized_tenant),
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> EndpointEventListResponse:
    """Get endpoint events across all devices, filterable by tenant."""
    query = select(EndpointEventModel)

    if tenant_id and tenant_id != "NONE":
        if isinstance(tenant_id, list):
            query = query.where(EndpointEventModel.tenant_id.in_([uuid.UUID(t) for t in tenant_id]))
        else:
            query = query.where(EndpointEventModel.tenant_id == uuid.UUID(tenant_id))

    if event_type:
        try:
            query = query.where(EndpointEventModel.event_type == EndpointEventType(event_type))
        except ValueError:
            pass

    if severity:
        try:
            query = query.where(EndpointEventModel.severity == EndpointEventSeverity(severity.upper()))
        except ValueError:
            pass

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(EndpointEventModel.detected_at.desc())
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    events = result.scalars().all()

    # Build a map of device_id -> hostname
    device_ids = list({e.device_id for e in events})
    hostname_map: dict[uuid.UUID, str] = {}
    if device_ids:
        dev_result = await db.execute(
            select(EndpointDeviceModel).where(EndpointDeviceModel.id.in_(device_ids))
        )
        for dev in dev_result.scalars().all():
            hostname_map[dev.id] = dev.hostname

    items = [
        EndpointEventResponse(
            id=e.id,
            device_id=e.device_id,
            hostname=hostname_map.get(e.device_id),
            event_type=e.event_type.value,
            severity=e.severity.value,
            title=e.title,
            description=e.description,
            process_name=e.process_name,
            command_line=e.command_line,
            user_context=e.user_context,
            source_ip=e.source_ip,
            metadata=e.event_metadata,
            detected_at=e.detected_at.isoformat(),
            received_at=e.received_at.isoformat(),
        )
        for e in events
    ]

    return EndpointEventListResponse(items=items, total=total)


@router.get(
    "/summary",
    response_model=EndpointSummary,
    summary="Get endpoint summary statistics",
)
async def get_endpoint_summary(
    tenant_id: str | list[str] | None = Depends(get_authorized_tenant),
    db: AsyncSession = Depends(get_db),
) -> EndpointSummary:
    """Get summary statistics for endpoint devices and events."""
    from datetime import timedelta

    # Base device query
    device_query = select(func.count()).select_from(EndpointDeviceModel)
    if tenant_id and tenant_id != "NONE":
        if isinstance(tenant_id, list):
            device_query = device_query.where(EndpointDeviceModel.tenant_id.in_([uuid.UUID(t) for t in tenant_id]))
        else:
            device_query = device_query.where(EndpointDeviceModel.tenant_id == uuid.UUID(tenant_id))

    total_devices = (await db.execute(device_query)).scalar() or 0

    # Active = has heartbeat in last 10 minutes
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    active_query = device_query.where(EndpointDeviceModel.last_heartbeat >= cutoff)
    active_devices = (await db.execute(active_query)).scalar() or 0

    # Events in last 24 hours
    events_cutoff = datetime.utcnow() - timedelta(hours=24)
    events_base = select(func.count()).select_from(EndpointEventModel).where(
        EndpointEventModel.detected_at >= events_cutoff
    )
    if tenant_id and tenant_id != "NONE":
        if isinstance(tenant_id, list):
            events_base = events_base.where(EndpointEventModel.tenant_id.in_([uuid.UUID(t) for t in tenant_id]))
        else:
            events_base = events_base.where(EndpointEventModel.tenant_id == uuid.UUID(tenant_id))

    total_events_24h = (await db.execute(events_base)).scalar() or 0

    critical_events = (
        await db.execute(
            events_base.where(EndpointEventModel.severity == EndpointEventSeverity.CRITICAL)
        )
    ).scalar() or 0

    high_events = (
        await db.execute(
            events_base.where(EndpointEventModel.severity == EndpointEventSeverity.HIGH)
        )
    ).scalar() or 0

    return EndpointSummary(
        total_devices=total_devices,
        active_devices=active_devices,
        total_events_24h=total_events_24h,
        critical_events_24h=critical_events,
        high_events_24h=high_events,
    )


@router.post(
    "/generate-token",
    response_model=GenerateTokenResponse,
    summary="Generate a new enrollment token",
)
async def generate_enrollment_token(
    tenant_id: str | list[str] | None = Depends(get_authorized_tenant),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateTokenResponse:
    """Generate a new enrollment token for a tenant. Admin only."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from src.models.settings import ApiKeyModel

    token = secrets.token_urlsafe(32)
    api_key = ApiKeyModel(
        name=f"Endpoint Enrollment Token",
        key_hash=_hash_token(token),
        key_prefix=token[:8],
        tenant_id=uuid.UUID(tenant_id) if tenant_id and tenant_id != "NONE" else None,
        is_active=True,
        created_by=user["username"],
    )
    db.add(api_key)
    await db.commit()

    return GenerateTokenResponse(
        enrollment_token=token,
        message="Enrollment token generated. Save it now — it cannot be retrieved later.",
    )
