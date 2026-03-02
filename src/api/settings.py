"""Settings API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.settings import SettingsService

router = APIRouter()


async def get_settings_service(db: AsyncSession = Depends(get_db)) -> SettingsService:
    """Dependency to get settings service."""
    return SettingsService(db)


# ========== Pydantic Models ==========

class SystemSettingsResponse(BaseModel):
    """System settings response."""
    audit_log_retention_days: int
    login_history_retention_days: int
    alert_history_retention_days: int
    auto_cleanup_enabled: bool
    cleanup_schedule: str
    api_rate_limit: int
    max_export_rows: int
    log_level: str
    created_at: str | None = None
    updated_at: str | None = None


class SystemSettingsUpdate(BaseModel):
    """System settings update request."""
    audit_log_retention_days: int | None = Field(None, ge=1, le=3650)
    login_history_retention_days: int | None = Field(None, ge=1, le=3650)
    alert_history_retention_days: int | None = Field(None, ge=1, le=3650)
    auto_cleanup_enabled: bool | None = None
    cleanup_schedule: str | None = None
    api_rate_limit: int | None = Field(None, ge=10, le=10000)
    max_export_rows: int | None = Field(None, ge=100, le=100000)
    log_level: str | None = Field(None, pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")


class UserPreferencesResponse(BaseModel):
    """User preferences response."""
    user_email: str
    timezone: str
    date_format: str
    theme: str
    email_notifications: bool
    discord_notifications: bool
    notification_min_severity: str
    default_dashboard_view: str
    refresh_interval_seconds: int
    created_at: str | None = None
    updated_at: str | None = None


class UserPreferencesUpdate(BaseModel):
    """User preferences update request."""
    timezone: str | None = None
    date_format: str | None = Field(None, pattern="^(ISO|US|EU)$")
    theme: str | None = Field(None, pattern="^(light|dark|system)$")
    email_notifications: bool | None = None
    discord_notifications: bool | None = None
    notification_min_severity: str | None = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    default_dashboard_view: str | None = None
    refresh_interval_seconds: int | None = Field(None, ge=10, le=3600)


class DetectionThresholdsResponse(BaseModel):
    """Detection thresholds response."""
    tenant_id: str | None = None

    # Impossible travel
    impossible_travel_enabled: bool
    impossible_travel_min_speed_kmh: float
    impossible_travel_time_window_minutes: int

    # New country
    new_country_enabled: bool
    new_country_learning_period_days: int

    # Brute force
    brute_force_enabled: bool
    brute_force_threshold: int
    brute_force_window_minutes: int

    # New IP
    new_ip_enabled: bool
    new_ip_learning_period_days: int

    # Multiple failures
    multiple_failures_enabled: bool
    multiple_failures_threshold: int
    multiple_failures_window_minutes: int

    # Risk scoring
    risk_score_base_multiplier: float

    created_at: str | None = None
    updated_at: str | None = None


class DetectionThresholdsUpdate(BaseModel):
    """Detection thresholds update request."""
    impossible_travel_enabled: bool | None = None
    impossible_travel_min_speed_kmh: float | None = Field(None, ge=100, le=5000)
    impossible_travel_time_window_minutes: int | None = Field(None, ge=5, le=1440)
    new_country_enabled: bool | None = None
    new_country_learning_period_days: int | None = Field(None, ge=1, le=90)
    brute_force_enabled: bool | None = None
    brute_force_threshold: int | None = Field(None, ge=1, le=100)
    brute_force_window_minutes: int | None = Field(None, ge=5, le=1440)
    new_ip_enabled: bool | None = None
    new_ip_learning_period_days: int | None = Field(None, ge=1, le=90)
    multiple_failures_enabled: bool | None = None
    multiple_failures_threshold: int | None = Field(None, ge=1, le=100)
    multiple_failures_window_minutes: int | None = Field(None, ge=5, le=1440)
    risk_score_base_multiplier: float | None = Field(None, ge=0.1, le=10.0)


class ApiKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str]
    tenant_id: str | None = None
    expires_days: int | None = Field(None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    """API key response (excludes hash)."""
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    tenant_id: str | None
    is_active: bool
    expires_at: str | None
    last_used_at: str | None
    created_by: str | None
    created_at: str


class ApiKeyCreateResponse(BaseModel):
    """API key creation response (includes full key once)."""
    id: str
    key: str
    name: str
    prefix: str
    message: str = "Store this key securely - it will not be shown again"


class ApiKeyUpdate(BaseModel):
    """API key update request."""
    name: str | None = Field(None, min_length=1, max_length=255)
    scopes: list[str] | None = None
    is_active: bool | None = None


class WebhookTestRequest(BaseModel):
    """Webhook test request."""
    webhook_url: str
    webhook_type: str = "discord"
    message: str = "🔔 Test notification from SpecterDefence"


class WebhookTestResponse(BaseModel):
    """Webhook test response."""
    success: bool
    message: str
    latency_ms: float | None = None


class ConfigExportRequest(BaseModel):
    """Configuration export request."""
    categories: list[str]
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ConfigExportResponse(BaseModel):
    """Configuration export response."""
    id: str
    name: str
    description: str | None
    categories: list[str]
    created_at: str
    download_url: str


class ConfigImportRequest(BaseModel):
    """Configuration import request."""
    config: dict[str, Any]
    overwrite: bool = False


class ConfigImportResponse(BaseModel):
    """Configuration import response."""
    imported: list[str]
    errors: list[str]
    message: str


class ConfigBackupResponse(BaseModel):
    """Configuration backup response."""
    id: str
    name: str
    description: str | None
    categories: list[str]
    created_by: str | None
    created_at: str


# ========== System Settings Endpoints ==========

@router.get(
    "/system",
    response_model=SystemSettingsResponse,
    summary="Get system settings",
    description="Retrieve system-wide configuration settings."
)
async def get_system_settings(
    service: SettingsService = Depends(get_settings_service)
) -> SystemSettingsResponse:
    """Get system settings."""
    settings = await service.get_system_settings()
    return SystemSettingsResponse(
        audit_log_retention_days=settings.audit_log_retention_days,
        login_history_retention_days=settings.login_history_retention_days,
        alert_history_retention_days=settings.alert_history_retention_days,
        auto_cleanup_enabled=settings.auto_cleanup_enabled,
        cleanup_schedule=settings.cleanup_schedule,
        api_rate_limit=settings.api_rate_limit,
        max_export_rows=settings.max_export_rows,
        log_level=settings.log_level,
        created_at=settings.created_at.isoformat() if settings.created_at else None,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
    )


@router.patch(
    "/system",
    response_model=SystemSettingsResponse,
    summary="Update system settings",
    description="Update system-wide configuration settings."
)
async def update_system_settings(
    update: SystemSettingsUpdate,
    service: SettingsService = Depends(get_settings_service)
) -> SystemSettingsResponse:
    """Update system settings."""
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    settings = await service.update_system_settings(updates)

    return SystemSettingsResponse(
        audit_log_retention_days=settings.audit_log_retention_days,
        login_history_retention_days=settings.login_history_retention_days,
        alert_history_retention_days=settings.alert_history_retention_days,
        auto_cleanup_enabled=settings.auto_cleanup_enabled,
        cleanup_schedule=settings.cleanup_schedule,
        api_rate_limit=settings.api_rate_limit,
        max_export_rows=settings.max_export_rows,
        log_level=settings.log_level,
        created_at=settings.created_at.isoformat() if settings.created_at else None,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
    )


# ========== User Preferences Endpoints ==========

@router.get(
    "/preferences/{user_email}",
    response_model=UserPreferencesResponse,
    summary="Get user preferences",
    description="Retrieve preferences for a specific user."
)
async def get_user_preferences(
    user_email: str,
    service: SettingsService = Depends(get_settings_service)
) -> UserPreferencesResponse:
    """Get user preferences."""
    prefs = await service.get_user_preferences(user_email)
    return UserPreferencesResponse(
        user_email=prefs.user_email,
        timezone=prefs.timezone,
        date_format=prefs.date_format,
        theme=prefs.theme,
        email_notifications=prefs.email_notifications,
        discord_notifications=prefs.discord_notifications,
        notification_min_severity=prefs.notification_min_severity,
        default_dashboard_view=prefs.default_dashboard_view,
        refresh_interval_seconds=prefs.refresh_interval_seconds,
        created_at=prefs.created_at.isoformat() if prefs.created_at else None,
        updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None,
    )


@router.patch(
    "/preferences/{user_email}",
    response_model=UserPreferencesResponse,
    summary="Update user preferences",
    description="Update preferences for a specific user."
)
async def update_user_preferences(
    user_email: str,
    update: UserPreferencesUpdate,
    service: SettingsService = Depends(get_settings_service)
) -> UserPreferencesResponse:
    """Update user preferences."""
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    prefs = await service.update_user_preferences(user_email, updates)

    return UserPreferencesResponse(
        user_email=prefs.user_email,
        timezone=prefs.timezone,
        date_format=prefs.date_format,
        theme=prefs.theme,
        email_notifications=prefs.email_notifications,
        discord_notifications=prefs.discord_notifications,
        notification_min_severity=prefs.notification_min_severity,
        default_dashboard_view=prefs.default_dashboard_view,
        refresh_interval_seconds=prefs.refresh_interval_seconds,
        created_at=prefs.created_at.isoformat() if prefs.created_at else None,
        updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None,
    )


# ========== Detection Thresholds Endpoints ==========

@router.get(
    "/detection",
    response_model=DetectionThresholdsResponse,
    summary="Get detection thresholds",
    description="Get anomaly detection thresholds for a tenant or global defaults."
)
async def get_detection_thresholds(
    tenant_id: str | None = None,
    service: SettingsService = Depends(get_settings_service)
) -> DetectionThresholdsResponse:
    """Get detection thresholds."""
    thresholds = await service.get_detection_thresholds(tenant_id)

    return DetectionThresholdsResponse(
        tenant_id=thresholds.tenant_id,
        impossible_travel_enabled=thresholds.impossible_travel_enabled,
        impossible_travel_min_speed_kmh=thresholds.impossible_travel_min_speed_kmh,
        impossible_travel_time_window_minutes=thresholds.impossible_travel_time_window_minutes,
        new_country_enabled=thresholds.new_country_enabled,
        new_country_learning_period_days=thresholds.new_country_learning_period_days,
        brute_force_enabled=thresholds.brute_force_enabled,
        brute_force_threshold=thresholds.brute_force_threshold,
        brute_force_window_minutes=thresholds.brute_force_window_minutes,
        new_ip_enabled=thresholds.new_ip_enabled,
        new_ip_learning_period_days=thresholds.new_ip_learning_period_days,
        multiple_failures_enabled=thresholds.multiple_failures_enabled,
        multiple_failures_threshold=thresholds.multiple_failures_threshold,
        multiple_failures_window_minutes=thresholds.multiple_failures_window_minutes,
        risk_score_base_multiplier=thresholds.risk_score_base_multiplier,
        created_at=thresholds.created_at.isoformat() if thresholds.created_at else None,
        updated_at=thresholds.updated_at.isoformat() if thresholds.updated_at else None,
    )


@router.patch(
    "/detection",
    response_model=DetectionThresholdsResponse,
    summary="Update detection thresholds",
    description="Update anomaly detection thresholds."
)
async def update_detection_thresholds(
    update: DetectionThresholdsUpdate,
    tenant_id: str | None = None,
    service: SettingsService = Depends(get_settings_service)
) -> DetectionThresholdsResponse:
    """Update detection thresholds."""
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    thresholds = await service.update_detection_thresholds(updates, tenant_id)

    return DetectionThresholdsResponse(
        tenant_id=thresholds.tenant_id,
        impossible_travel_enabled=thresholds.impossible_travel_enabled,
        impossible_travel_min_speed_kmh=thresholds.impossible_travel_min_speed_kmh,
        impossible_travel_time_window_minutes=thresholds.impossible_travel_time_window_minutes,
        new_country_enabled=thresholds.new_country_enabled,
        new_country_learning_period_days=thresholds.new_country_learning_period_days,
        brute_force_enabled=thresholds.brute_force_enabled,
        brute_force_threshold=thresholds.brute_force_threshold,
        brute_force_window_minutes=thresholds.brute_force_window_minutes,
        new_ip_enabled=thresholds.new_ip_enabled,
        new_ip_learning_period_days=thresholds.new_ip_learning_period_days,
        multiple_failures_enabled=thresholds.multiple_failures_enabled,
        multiple_failures_threshold=thresholds.multiple_failures_threshold,
        multiple_failures_window_minutes=thresholds.multiple_failures_window_minutes,
        risk_score_base_multiplier=thresholds.risk_score_base_multiplier,
        created_at=thresholds.created_at.isoformat() if thresholds.created_at else None,
        updated_at=thresholds.updated_at.isoformat() if thresholds.updated_at else None,
    )


# ========== API Key Management Endpoints ==========

@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Create a new API key for programmatic access."
)
async def create_api_key(
    request: ApiKeyCreate,
    created_by: str | None = None,
    service: SettingsService = Depends(get_settings_service)
) -> ApiKeyCreateResponse:
    """Create a new API key."""
    result = await service.create_api_key(
        name=request.name,
        scopes=request.scopes,
        created_by=created_by,
        tenant_id=request.tenant_id,
        expires_days=request.expires_days
    )

    return ApiKeyCreateResponse(
        id=result["id"],
        key=result["key"],
        name=result["name"],
        prefix=result["prefix"]
    )


@router.get(
    "/api-keys",
    response_model=list[ApiKeyResponse],
    summary="List API keys",
    description="List all API keys."
)
async def list_api_keys(
    tenant_id: str | None = None,
    include_inactive: bool = False,
    service: SettingsService = Depends(get_settings_service)
) -> list[ApiKeyResponse]:
    """List API keys."""
    keys = await service.list_api_keys(tenant_id, include_inactive)

    return [
        ApiKeyResponse(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            tenant_id=k.tenant_id,
            is_active=k.is_active,
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            created_by=k.created_by,
            created_at=k.created_at.isoformat()
        )
        for k in keys
    ]


@router.get(
    "/api-keys/{key_id}",
    response_model=ApiKeyResponse,
    summary="Get API key",
    description="Get details of a specific API key."
)
async def get_api_key(
    key_id: str,
    service: SettingsService = Depends(get_settings_service)
) -> ApiKeyResponse:
    """Get an API key."""
    key = await service.get_api_key(key_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return ApiKeyResponse(
        id=str(key.id),
        name=key.name,
        key_prefix=key.key_prefix,
        scopes=key.scopes,
        tenant_id=key.tenant_id,
        is_active=key.is_active,
        expires_at=key.expires_at.isoformat() if key.expires_at else None,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        created_by=key.created_by,
        created_at=key.created_at.isoformat()
    )


@router.patch(
    "/api-keys/{key_id}",
    response_model=ApiKeyResponse,
    summary="Update API key",
    description="Update an API key's name, scopes, or status."
)
async def update_api_key(
    key_id: str,
    update: ApiKeyUpdate,
    service: SettingsService = Depends(get_settings_service)
) -> ApiKeyResponse:
    """Update an API key."""
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    key = await service.update_api_key(key_id, updates)

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return ApiKeyResponse(
        id=str(key.id),
        name=key.name,
        key_prefix=key.key_prefix,
        scopes=key.scopes,
        tenant_id=key.tenant_id,
        is_active=key.is_active,
        expires_at=key.expires_at.isoformat() if key.expires_at else None,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        created_by=key.created_by,
        created_at=key.created_at.isoformat()
    )


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
    description="Revoke an API key (soft delete)."
)
async def revoke_api_key(
    key_id: str,
    service: SettingsService = Depends(get_settings_service)
) -> None:
    """Revoke an API key."""
    revoked = await service.revoke_api_key(key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


# ========== Webhook Test Endpoint ==========

@router.post(
    "/webhooks/test",
    response_model=WebhookTestResponse,
    summary="Test webhook",
    description="Send a test notification to a webhook URL."
)
async def send_test_webhook(
    request: WebhookTestRequest
) -> WebhookTestResponse:
    """Test a webhook URL."""
    from datetime import datetime

    import aiohttp

    start_time = datetime.now()

    try:
        if request.webhook_type.lower() == "discord":
            payload = {
                "content": None,
                "embeds": [{
                    "title": "🧪 Webhook Test",
                    "description": request.message,
                    "color": 3447003,
                    "timestamp": datetime.now().isoformat(),
                    "footer": {
                        "text": "SpecterDefence Settings Test"
                    }
                }]
            }
        else:
            payload = {"text": request.message}

        async with aiohttp.ClientSession() as session, session.post(
            request.webhook_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            latency = (datetime.now() - start_time).total_seconds() * 1000

            if response.status in [200, 204]:
                return WebhookTestResponse(
                    success=True,
                    message=f"Webhook test successful (HTTP {response.status})",
                    latency_ms=round(latency, 2)
                )
            else:
                return WebhookTestResponse(
                    success=False,
                    message=f"Webhook returned HTTP {response.status}",
                    latency_ms=round(latency, 2)
                )
    except TimeoutError:
        return WebhookTestResponse(
            success=False,
            message="Webhook test timed out after 10 seconds"
        )
    except Exception as e:
        return WebhookTestResponse(
            success=False,
            message=f"Webhook test failed: {str(e)}"
        )


# ========== Configuration Import/Export Endpoints ==========

@router.post(
    "/config/export",
    response_model=ConfigExportResponse,
    summary="Export configuration",
    description="Export system configuration to JSON."
)
async def export_configuration(
    request: ConfigExportRequest,
    created_by: str | None = None,
    service: SettingsService = Depends(get_settings_service)
) -> ConfigExportResponse:
    """Export configuration."""
    result = await service.export_configuration(
        categories=request.categories,
        name=request.name,
        description=request.description,
        created_by=created_by
    )

    return ConfigExportResponse(
        id=result["id"],
        name=result["name"],
        description=result.get("description"),
        categories=result["categories"],
        created_at=result["created_at"],
        download_url=f"/api/v1/settings/config/export/{result['id']}/download"
    )


@router.get(
    "/config/export/{backup_id}/download",
    summary="Download configuration export",
    description="Download a configuration export as JSON file."
)
async def download_configuration(
    backup_id: str,
    service: SettingsService = Depends(get_settings_service)
):
    """Download configuration export."""
    backup = await service.get_configuration_backup(backup_id)
    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration backup not found"
        )

    from fastapi.responses import JSONResponse
    return JSONResponse(
        content=backup.config_data,
        headers={
            "Content-Disposition": f"attachment; filename=specterdefence-config-{backup.name}.json"
        }
    )


@router.post(
    "/config/import",
    response_model=ConfigImportResponse,
    summary="Import configuration",
    description="Import system configuration from JSON."
)
async def import_configuration(
    request: ConfigImportRequest,
    service: SettingsService = Depends(get_settings_service)
) -> ConfigImportResponse:
    """Import configuration."""
    result = await service.import_configuration(
        config_data=request.config,
        overwrite=request.overwrite
    )

    return ConfigImportResponse(
        imported=result["imported"],
        errors=result["errors"],
        message="Configuration imported successfully" if not result["errors"] else "Import completed with errors"
    )


@router.get(
    "/config/backups",
    response_model=list[ConfigBackupResponse],
    summary="List configuration backups",
    description="List all configuration backups."
)
async def list_configuration_backups(
    service: SettingsService = Depends(get_settings_service)
) -> list[ConfigBackupResponse]:
    """List configuration backups."""
    backups = await service.list_configuration_backups()

    return [
        ConfigBackupResponse(
            id=str(b.id),
            name=b.name,
            description=b.description,
            categories=b.categories,
            created_by=b.created_by,
            created_at=b.created_at.isoformat()
        )
        for b in backups
    ]


@router.delete(
    "/config/backups/{backup_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete configuration backup",
    description="Delete a configuration backup."
)
async def delete_configuration_backup(
    backup_id: str,
    service: SettingsService = Depends(get_settings_service)
) -> None:
    """Delete a configuration backup."""
    deleted = await service.delete_configuration_backup(backup_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration backup not found"
        )


# ========== Tenant Settings Endpoints ==========

@router.get(
    "/tenants/{tenant_id}",
    summary="Get tenant-specific settings",
    description="Get all settings for a specific tenant including detection thresholds."
)
async def get_tenant_settings(
    tenant_id: str,
    service: SettingsService = Depends(get_settings_service)
) -> dict[str, Any]:
    """Get tenant settings."""
    thresholds = await service.get_detection_thresholds(tenant_id)

    return {
        "tenant_id": tenant_id,
        "detection": {
            "impossible_travel_enabled": thresholds.impossible_travel_enabled,
            "impossible_travel_min_speed_kmh": thresholds.impossible_travel_min_speed_kmh,
            "impossible_travel_time_window_minutes": thresholds.impossible_travel_time_window_minutes,
            "new_country_enabled": thresholds.new_country_enabled,
            "new_country_learning_period_days": thresholds.new_country_learning_period_days,
            "brute_force_enabled": thresholds.brute_force_enabled,
            "brute_force_threshold": thresholds.brute_force_threshold,
            "brute_force_window_minutes": thresholds.brute_force_window_minutes,
            "new_ip_enabled": thresholds.new_ip_enabled,
            "new_ip_learning_period_days": thresholds.new_ip_learning_period_days,
            "multiple_failures_enabled": thresholds.multiple_failures_enabled,
            "multiple_failures_threshold": thresholds.multiple_failures_threshold,
            "multiple_failures_window_minutes": thresholds.multiple_failures_window_minutes,
            "risk_score_base_multiplier": thresholds.risk_score_base_multiplier,
        }
    }
