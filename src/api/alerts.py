"""Alert API endpoints for SpecterDefence."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.engine import AlertEngine
from src.alerts.rules import AlertRuleService
from src.database import get_db
from src.models.alerts import (
    SeverityLevel,
)

router = APIRouter()


# Pydantic models for API requests/responses

class WebhookCreate(BaseModel):
    """Request model for creating a webhook."""
    name: str = Field(..., min_length=1, max_length=255, description="Display name for the webhook")
    webhook_url: str = Field(..., min_length=10, description="Discord webhook URL")
    webhook_type: str = Field(default="discord", description="Type of webhook (discord, slack)")


class WebhookResponse(BaseModel):
    """Response model for a webhook."""
    id: UUID
    name: str
    webhook_type: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    """Response model for webhook test."""
    success: bool
    message: str


class RuleCreate(BaseModel):
    """Request model for creating an alert rule."""
    name: str = Field(..., min_length=1, max_length=255, description="Display name for the rule")
    event_types: list[str] = Field(..., description="List of event types to match")
    min_severity: str = Field(..., description="Minimum severity level (LOW, MEDIUM, HIGH, CRITICAL)")
    cooldown_minutes: int = Field(default=30, ge=1, le=1440, description="Cooldown period in minutes")


class RuleUpdate(BaseModel):
    """Request model for updating an alert rule."""
    name: str | None = Field(None, min_length=1, max_length=255)
    event_types: list[str] | None = None
    min_severity: str | None = None
    cooldown_minutes: int | None = Field(None, ge=1, le=1440)
    is_active: bool | None = None


class RuleResponse(BaseModel):
    """Response model for an alert rule."""
    id: UUID
    name: str
    event_types: list[str]
    min_severity: str
    cooldown_minutes: int
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    """Response model for alert history."""
    id: UUID
    rule_id: UUID | None
    webhook_id: UUID
    severity: str
    event_type: str
    user_email: str | None
    title: str
    message: str
    metadata: dict
    sent_at: str

    class Config:
        from_attributes = True


class AlertHistoryList(BaseModel):
    """Response model for alert history list."""
    total: int
    items: list[AlertHistoryResponse]
    limit: int
    offset: int


# Dependencies

async def get_rule_service(db: AsyncSession = Depends(get_db)) -> AlertRuleService:
    """Dependency to get alert rule service."""
    return AlertRuleService(db)


async def get_alert_engine(db: AsyncSession = Depends(get_db)) -> AlertEngine:
    """Dependency to get alert engine."""
    return AlertEngine(db)


# Webhook endpoints

@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook",
    description="Create a new Discord webhook for alerts."
)
async def create_webhook(
    webhook: WebhookCreate,
    tenant_id: str | None = None,
    service: AlertRuleService = Depends(get_rule_service)
) -> WebhookResponse:
    """Create a new alert webhook.
    
    Args:
        webhook: Webhook creation data
        tenant_id: Optional tenant ID for tenant-specific webhook
        service: Alert rule service
        
    Returns:
        Created webhook details
    """
    try:
        created = await service.create_webhook(
            name=webhook.name,
            webhook_url=webhook.webhook_url,
            webhook_type=webhook.webhook_type,
            tenant_id=tenant_id,
        )
        return WebhookResponse(
            id=created.id,
            name=created.name,
            webhook_type=created.webhook_type,
            is_active=created.is_active,
            created_at=created.created_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create webhook: {str(e)}"
        ) from e


@router.get(
    "/webhooks",
    response_model=list[WebhookResponse],
    summary="List webhooks",
    description="List all configured alert webhooks."
)
async def list_webhooks(
    tenant_id: str | None = None,
    include_inactive: bool = False,
    service: AlertRuleService = Depends(get_rule_service)
) -> list[WebhookResponse]:
    """List all alert webhooks.
    
    Args:
        tenant_id: Filter by tenant ID
        include_inactive: Include inactive webhooks
        service: Alert rule service
        
    Returns:
        List of webhook configurations
    """
    webhooks = await service.list_webhooks(
        tenant_id=tenant_id,
        include_inactive=include_inactive,
    )

    return [
        WebhookResponse(
            id=w.id,
            name=w.name,
            webhook_type=w.webhook_type,
            is_active=w.is_active,
            created_at=w.created_at.isoformat(),
        )
        for w in webhooks
    ]


@router.post(
    "/webhooks/{webhook_id}/test",
    response_model=WebhookTestResponse,
    summary="Test webhook",
    description="Send a test message to a webhook."
)
async def test_webhook(
    webhook_id: UUID,
    service: AlertRuleService = Depends(get_rule_service)
) -> WebhookTestResponse:
    """Test a webhook by sending a test message.
    
    Args:
        webhook_id: Webhook UUID
        service: Alert rule service
        
    Returns:
        Test result
    """
    from src.alerts.discord import DiscordWebhookClient
    from src.services.encryption import encryption_service

    webhook = await service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook with ID {webhook_id} not found"
        )

    try:
        decrypted_url = encryption_service.decrypt(webhook.webhook_url)
        client = DiscordWebhookClient(decrypted_url)

        success = await client.test_webhook()
        await client.close()

        if success:
            return WebhookTestResponse(
                success=True,
                message="Test message sent successfully!"
            )
        else:
            return WebhookTestResponse(
                success=False,
                message="Failed to send test message. Check webhook URL."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook test failed: {str(e)}"
        ) from e


@router.delete(
    "/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook",
    description="Delete an alert webhook."
)
async def delete_webhook(
    webhook_id: UUID,
    service: AlertRuleService = Depends(get_rule_service)
) -> None:
    """Delete an alert webhook.
    
    Args:
        webhook_id: Webhook UUID
        service: Alert rule service
        
    Raises:
        HTTPException: If webhook not found
    """
    deleted = await service.delete_webhook(webhook_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook with ID {webhook_id} not found"
        )


# Rule endpoints

@router.post(
    "/rules",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create alert rule",
    description="Create a new alert rule."
)
async def create_rule(
    rule: RuleCreate,
    tenant_id: str | None = None,
    service: AlertRuleService = Depends(get_rule_service)
) -> RuleResponse:
    """Create a new alert rule.
    
    Args:
        rule: Rule creation data
        tenant_id: Optional tenant ID for tenant-specific rule
        service: Alert rule service
        
    Returns:
        Created rule details
    """
    try:
        created = await service.create_rule(
            name=rule.name,
            event_types=rule.event_types,
            min_severity=rule.min_severity,
            cooldown_minutes=rule.cooldown_minutes,
            tenant_id=tenant_id,
        )
        return RuleResponse(
            id=created.id,
            name=created.name,
            event_types=created.event_types,
            min_severity=created.min_severity.value,
            cooldown_minutes=created.cooldown_minutes,
            is_active=created.is_active,
            created_at=created.created_at.isoformat(),
            updated_at=created.updated_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rule: {str(e)}"
        ) from e


@router.get(
    "/rules",
    response_model=list[RuleResponse],
    summary="List alert rules",
    description="List all alert rules."
)
async def list_rules(
    tenant_id: str | None = None,
    include_inactive: bool = False,
    service: AlertRuleService = Depends(get_rule_service)
) -> list[RuleResponse]:
    """List all alert rules.
    
    Args:
        tenant_id: Filter by tenant ID
        include_inactive: Include inactive rules
        service: Alert rule service
        
    Returns:
        List of alert rules
    """
    rules = await service.list_rules(
        tenant_id=tenant_id,
        include_inactive=include_inactive,
    )

    return [
        RuleResponse(
            id=r.id,
            name=r.name,
            event_types=r.event_types,
            min_severity=r.min_severity.value,
            cooldown_minutes=r.cooldown_minutes,
            is_active=r.is_active,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in rules
    ]


@router.get(
    "/rules/{rule_id}",
    response_model=RuleResponse,
    summary="Get alert rule",
    description="Get a specific alert rule by ID."
)
async def get_rule(
    rule_id: UUID,
    service: AlertRuleService = Depends(get_rule_service)
) -> RuleResponse:
    """Get a specific alert rule.
    
    Args:
        rule_id: Rule UUID
        service: Alert rule service
        
    Returns:
        Rule details
        
    Raises:
        HTTPException: If rule not found
    """
    rule = await service.get_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )

    return RuleResponse(
        id=rule.id,
        name=rule.name,
        event_types=rule.event_types,
        min_severity=rule.min_severity.value,
        cooldown_minutes=rule.cooldown_minutes,
        is_active=rule.is_active,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


@router.put(
    "/rules/{rule_id}",
    response_model=RuleResponse,
    summary="Update alert rule",
    description="Update an existing alert rule."
)
async def update_rule(
    rule_id: UUID,
    updates: RuleUpdate,
    service: AlertRuleService = Depends(get_rule_service)
) -> RuleResponse:
    """Update an alert rule.
    
    Args:
        rule_id: Rule UUID
        updates: Fields to update
        service: Alert rule service
        
    Returns:
        Updated rule details
        
    Raises:
        HTTPException: If rule not found
    """
    update_dict = updates.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    updated = await service.update_rule(rule_id, update_dict)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )

    return RuleResponse(
        id=updated.id,
        name=updated.name,
        event_types=updated.event_types,
        min_severity=updated.min_severity.value,
        cooldown_minutes=updated.cooldown_minutes,
        is_active=updated.is_active,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete alert rule",
    description="Delete an alert rule."
)
async def delete_rule(
    rule_id: UUID,
    service: AlertRuleService = Depends(get_rule_service)
) -> None:
    """Delete an alert rule.
    
    Args:
        rule_id: Rule UUID
        service: Alert rule service
        
    Raises:
        HTTPException: If rule not found
    """
    deleted = await service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )


# Alert history endpoints

@router.get(
    "/history",
    response_model=AlertHistoryList,
    summary="Get alert history",
    description="Get history of sent alerts with optional filtering."
)
async def get_alert_history(
    tenant_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    user_email: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    engine: AlertEngine = Depends(get_alert_engine)
) -> AlertHistoryList:
    """Get alert history.
    
    Args:
        tenant_id: Filter by tenant
        event_type: Filter by event type
        severity: Filter by severity level
        user_email: Filter by user email
        limit: Maximum results (1-1000)
        offset: Offset for pagination
        engine: Alert engine
        
    Returns:
        Paginated alert history
    """
    severity_enum = None
    if severity:
        try:
            severity_enum = SeverityLevel(severity.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity level: {severity}"
            )

    history = await engine.get_alert_history(
        tenant_id=tenant_id,
        event_type=event_type,
        severity=severity_enum,
        user_email=user_email,
        limit=limit,
        offset=offset,
    )

    return AlertHistoryList(
        total=len(history),
        items=[
            AlertHistoryResponse(
                id=h.id,
                rule_id=h.rule_id,
                webhook_id=h.webhook_id,
                severity=h.severity.value,
                event_type=h.event_type,
                user_email=h.user_email,
                title=h.title,
                message=h.message,
                metadata=h.alert_metadata,
                sent_at=h.sent_at.isoformat(),
            )
            for h in history
        ],
        limit=limit,
        offset=offset,
    )
