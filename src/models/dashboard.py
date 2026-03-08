"""Dashboard data models for SpecterDefence."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TimeRange(StrEnum):
    """Time range options for dashboard data."""

    DAY_7 = "7d"
    DAY_30 = "30d"
    DAY_90 = "90d"


class LoginActivityPoint(BaseModel):
    """Single point in login activity timeline."""

    timestamp: datetime
    successful_logins: int
    failed_logins: int
    total_logins: int


class LoginActivityTimeline(BaseModel):
    """Login activity timeline data."""

    data: list[LoginActivityPoint]
    time_range: TimeRange
    total_successful: int
    total_failed: int
    change_percent: float = Field(description="Percentage change vs previous period")


class GeoLocationPoint(BaseModel):
    """Geographic location data point."""

    country_code: str
    country_name: str
    latitude: float
    longitude: float
    login_count: int
    user_count: int
    risk_score_avg: float


class GeoHeatmapData(BaseModel):
    """Geographic heatmap data."""

    locations: list[GeoLocationPoint]
    total_countries: int
    top_country: str | None = None
    top_country_count: int = 0


class AnomalyTrendPoint(BaseModel):
    """Single point in anomaly trend."""

    date: datetime
    count: int
    types: dict[str, int] = Field(default_factory=dict, description="Count by anomaly type")


class AnomalyTrendData(BaseModel):
    """Anomaly trend data over time."""

    data: list[AnomalyTrendPoint]
    time_range: TimeRange
    total_anomalies: int
    top_type: str | None = None
    change_percent: float


class TopRiskUser(BaseModel):
    """Top risk user entry."""

    user_email: str
    tenant_id: uuid.UUID
    risk_score: int
    anomaly_count: int
    last_anomaly_time: datetime | None = None
    top_anomaly_types: list[str] = Field(default_factory=list)
    country_count: int = 0


class TopRiskUsersData(BaseModel):
    """Top risk users list."""

    users: list[TopRiskUser]
    total_users: int
    avg_risk_score: float


class AlertVolumePoint(BaseModel):
    """Single point in alert volume timeline."""

    timestamp: datetime
    critical: int
    high: int
    medium: int
    low: int
    total: int


class AlertVolumeData(BaseModel):
    """Alert volume data by severity."""

    data: list[AlertVolumePoint]
    time_range: TimeRange
    total_by_severity: dict[str, int]
    peak_volume: int
    peak_time: datetime | None = None


class AnomalyTypeBreakdown(BaseModel):
    """Breakdown of anomalies by type."""

    type: str
    count: int
    percentage: float
    avg_risk_score: float


class DashboardSummary(BaseModel):
    """Dashboard summary statistics."""

    total_logins_24h: int
    failed_logins_24h: int
    active_users_24h: int
    anomalies_today: int
    alerts_today: int
    active_tenants: int
    avg_risk_score: float
    login_success_rate: float
    top_threats: list[str] = Field(default_factory=list)

    # Posture metrics
    mfa_compliance_rate: float = 0.0
    high_risk_oauth_apps: int = 0
    disabled_ca_policies: int = 0
    suspicious_mailbox_rules: int = 0
    total_protected_users: int = 0


class DashboardDataResponse(BaseModel):
    """Complete dashboard data response."""

    summary: DashboardSummary
    login_timeline: LoginActivityTimeline
    geo_heatmap: GeoHeatmapData
    anomaly_trend: AnomalyTrendData
    top_risk_users: TopRiskUsersData
    alert_volume: AlertVolumeData
    anomaly_breakdown: list[AnomalyTypeBreakdown]
    generated_at: datetime
    time_range: TimeRange


class ExportRequest(BaseModel):
    """Export dashboard data request."""

    time_range: TimeRange = TimeRange.DAY_30
    format: str = Field(default="pdf", pattern="^(pdf|png|csv|json)$")
    charts: list[str] = Field(
        default_factory=lambda: ["all"],
        description="Charts to export: all, timeline, heatmap, anomalies, alerts, users",
    )


class ExportResponse(BaseModel):
    """Export response."""

    download_url: str
    filename: str
    format: str
    expires_at: datetime
