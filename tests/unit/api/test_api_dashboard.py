"""Unit tests for dashboard API endpoints."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

# Import endpoint functions with aliases to avoid pytest collection issues
import src.api.dashboard as dashboard_api
from src.models.dashboard import (
    AlertVolumeData,
    AnomalyTrendData,
    AnomalyTypeBreakdown,
    DashboardDataResponse,
    DashboardSummary,
    GeoHeatmapData,
    LoginActivityTimeline,
    TimeRange,
    TopRiskUsersData,
)
from src.services.dashboard import DashboardService


class TestDashboardSummaryEndpoint:
    """Test cases for dashboard summary endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_success(self, mock_service):
        """Test successful dashboard summary retrieval."""
        mock_summary = DashboardSummary(
            total_logins_24h=1000,
            failed_logins_24h=50,
            active_users_24h=150,
            anomalies_today=10,
            alerts_today=25,
            active_tenants=5,
            avg_risk_score=35.5,
            login_success_rate=95.0,
            top_threats=["impossible_travel", "new_country"],
        )
        mock_service.get_summary_stats.return_value = mock_summary

        result = await dashboard_api.get_dashboard_summary(tenant_id=None, service=mock_service)

        assert result.total_logins_24h == 1000
        assert result.failed_logins_24h == 50
        assert result.anomalies_today == 10
        assert result.top_threats == ["impossible_travel", "new_country"]
        mock_service.get_summary_stats.assert_called_once_with(tenant_id=None)

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_with_tenant(self, mock_service):
        """Test dashboard summary with tenant filter."""
        tenant_id = str(uuid4())
        mock_summary = DashboardSummary(
            total_logins_24h=500,
            failed_logins_24h=20,
            active_users_24h=75,
            anomalies_today=5,
            alerts_today=10,
            active_tenants=1,
            avg_risk_score=40.0,
            login_success_rate=96.0,
            top_threats=[],
        )
        mock_service.get_summary_stats.return_value = mock_summary

        result = await dashboard_api.get_dashboard_summary(
            tenant_id=tenant_id, service=mock_service
        )

        assert result.total_logins_24h == 500
        mock_service.get_summary_stats.assert_called_once_with(tenant_id=tenant_id)

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_error(self, mock_service):
        """Test dashboard summary with service error."""
        mock_service.get_summary_stats.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await dashboard_api.get_dashboard_summary(tenant_id=None, service=mock_service)

        assert exc_info.value.status_code == 500
        assert "Error fetching dashboard summary" in exc_info.value.detail


class TestLoginTimelineEndpoint:
    """Test cases for login timeline endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_get_login_timeline_success(self, mock_service):
        """Test successful login timeline retrieval."""
        from src.models.dashboard import LoginActivityPoint

        now = datetime.utcnow()
        mock_timeline = LoginActivityTimeline(
            data=[
                LoginActivityPoint(
                    timestamp=now - timedelta(hours=1),
                    successful_logins=100,
                    failed_logins=5,
                    total_logins=105,
                ),
                LoginActivityPoint(
                    timestamp=now, successful_logins=120, failed_logins=3, total_logins=123
                ),
            ],
            time_range=TimeRange.DAY_7,
            total_successful=220,
            total_failed=8,
            change_percent=12.5,
        )
        mock_service.get_login_activity_timeline.return_value = mock_timeline

        result = await dashboard_api.get_login_timeline(
            time_range=TimeRange.DAY_7, tenant_id=None, service=mock_service
        )

        assert len(result.data) == 2
        assert result.total_successful == 220
        assert result.change_percent == 12.5
        mock_service.get_login_activity_timeline.assert_called_once_with(
            time_range=TimeRange.DAY_7, tenant_id=None
        )

    @pytest.mark.asyncio
    async def test_get_login_timeline_error(self, mock_service):
        """Test login timeline with service error."""
        mock_service.get_login_activity_timeline.side_effect = Exception("Query failed")

        with pytest.raises(HTTPException) as exc_info:
            await dashboard_api.get_login_timeline(
                time_range=TimeRange.DAY_30, tenant_id=None, service=mock_service
            )

        assert exc_info.value.status_code == 500
        assert "Error fetching login timeline" in exc_info.value.detail


class TestGeoHeatmapEndpoint:
    """Test cases for geo heatmap endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_get_geo_heatmap_success(self, mock_service):
        """Test successful geo heatmap retrieval."""
        from src.models.dashboard import GeoLocationPoint

        mock_heatmap = GeoHeatmapData(
            locations=[
                GeoLocationPoint(
                    country_code="US",
                    country_name="United States",
                    latitude=37.0902,
                    longitude=-95.7129,
                    login_count=500,
                    user_count=100,
                    risk_score_avg=25.5,
                ),
                GeoLocationPoint(
                    country_code="GB",
                    country_name="United Kingdom",
                    latitude=55.3781,
                    longitude=-3.4360,
                    login_count=200,
                    user_count=50,
                    risk_score_avg=30.0,
                ),
            ],
            total_countries=2,
            top_country="United States",
            top_country_count=500,
        )
        mock_service.get_geo_heatmap_data.return_value = mock_heatmap

        result = await dashboard_api.get_geo_heatmap(
            time_range=TimeRange.DAY_30, tenant_id=None, service=mock_service
        )

        assert len(result.locations) == 2
        assert result.total_countries == 2
        assert result.top_country == "United States"
        mock_service.get_geo_heatmap_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_geo_heatmap_empty(self, mock_service):
        """Test geo heatmap with no data."""
        mock_heatmap = GeoHeatmapData(
            locations=[], total_countries=0, top_country=None, top_country_count=0
        )
        mock_service.get_geo_heatmap_data.return_value = mock_heatmap

        result = await dashboard_api.get_geo_heatmap(
            time_range=TimeRange.DAY_7, tenant_id=None, service=mock_service
        )

        assert len(result.locations) == 0
        assert result.total_countries == 0


class TestAnomalyTrendEndpoint:
    """Test cases for anomaly trend endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_get_anomaly_trend_success(self, mock_service):
        """Test successful anomaly trend retrieval."""
        from src.models.dashboard import AnomalyTrendPoint

        now = datetime.utcnow()
        mock_trend = AnomalyTrendData(
            data=[
                AnomalyTrendPoint(
                    date=now - timedelta(days=1),
                    count=5,
                    types={"impossible_travel": 3, "new_country": 2},
                ),
                AnomalyTrendPoint(
                    date=now, count=3, types={"impossible_travel": 2, "new_country": 1}
                ),
            ],
            time_range=TimeRange.DAY_7,
            total_anomalies=8,
            top_type="impossible_travel",
            change_percent=-25.0,
        )
        mock_service.get_anomaly_trend.return_value = mock_trend

        result = await dashboard_api.get_anomaly_trend(
            time_range=TimeRange.DAY_7, tenant_id=None, service=mock_service
        )

        assert len(result.data) == 2
        assert result.total_anomalies == 8
        assert result.top_type == "impossible_travel"
        assert result.change_percent == -25.0


class TestTopRiskUsersEndpoint:
    """Test cases for top risk users endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_get_top_risk_users_success(self, mock_service):
        """Test successful top risk users retrieval."""
        from src.models.dashboard import TopRiskUser

        mock_users = TopRiskUsersData(
            users=[
                TopRiskUser(
                    user_email="user1@example.com",
                    tenant_id="tenant-1",
                    risk_score=85,
                    anomaly_count=10,
                    last_anomaly_time=datetime.utcnow(),
                    top_anomaly_types=["impossible_travel", "new_country"],
                    country_count=5,
                ),
                TopRiskUser(
                    user_email="user2@example.com",
                    tenant_id="tenant-1",
                    risk_score=70,
                    anomaly_count=7,
                    top_anomaly_types=["new_country"],
                    country_count=3,
                ),
            ],
            total_users=2,
            avg_risk_score=77.5,
        )
        mock_service.get_top_risk_users.return_value = mock_users

        result = await dashboard_api.get_top_risk_users(
            limit=10, tenant_id=None, service=mock_service
        )

        assert len(result.users) == 2
        assert result.users[0].risk_score == 85
        assert result.avg_risk_score == 77.5
        mock_service.get_top_risk_users.assert_called_once_with(limit=10, tenant_id=None)

    @pytest.mark.asyncio
    async def test_get_top_risk_users_with_limit(self, mock_service):
        """Test top risk users with custom limit."""
        mock_service.get_top_risk_users.return_value = TopRiskUsersData(
            users=[], total_users=0, avg_risk_score=0.0
        )

        await dashboard_api.get_top_risk_users(
            limit=5, tenant_id="tenant-123", service=mock_service
        )

        mock_service.get_top_risk_users.assert_called_once_with(limit=5, tenant_id="tenant-123")


class TestAlertVolumeEndpoint:
    """Test cases for alert volume endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_get_alert_volume_success(self, mock_service):
        """Test successful alert volume retrieval."""
        from src.models.dashboard import AlertVolumePoint

        now = datetime.utcnow()
        mock_volume = AlertVolumeData(
            data=[
                AlertVolumePoint(
                    timestamp=now - timedelta(days=1),
                    critical=1,
                    high=3,
                    medium=5,
                    low=10,
                    total=19,
                ),
                AlertVolumePoint(timestamp=now, critical=0, high=2, medium=4, low=8, total=14),
            ],
            time_range=TimeRange.DAY_7,
            total_by_severity={"CRITICAL": 1, "HIGH": 5, "MEDIUM": 9, "LOW": 18},
            peak_volume=19,
            peak_time=now - timedelta(days=1),
        )
        mock_service.get_alert_volume.return_value = mock_volume

        result = await dashboard_api.get_alert_volume(
            time_range=TimeRange.DAY_7, tenant_id=None, service=mock_service
        )

        assert len(result.data) == 2
        assert result.peak_volume == 19
        assert result.total_by_severity["CRITICAL"] == 1


class TestAnomalyBreakdownEndpoint:
    """Test cases for anomaly breakdown endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_get_anomaly_breakdown_success(self, mock_service):
        """Test successful anomaly breakdown retrieval."""
        mock_breakdown = [
            AnomalyTypeBreakdown(
                type="impossible_travel", count=50, percentage=50.0, avg_risk_score=75.0
            ),
            AnomalyTypeBreakdown(
                type="new_country", count=30, percentage=30.0, avg_risk_score=60.0
            ),
            AnomalyTypeBreakdown(
                type="failed_login", count=20, percentage=20.0, avg_risk_score=40.0
            ),
        ]
        mock_service.get_anomaly_breakdown.return_value = mock_breakdown

        result = await dashboard_api.get_anomaly_breakdown(
            time_range=TimeRange.DAY_30, tenant_id=None, service=mock_service
        )

        assert len(result) == 3
        assert result[0].type == "impossible_travel"
        assert result[0].percentage == 50.0


class TestFullDashboardEndpoint:
    """Test cases for full dashboard endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_get_full_dashboard_success(self, mock_service):
        """Test successful full dashboard retrieval."""
        from src.models.dashboard import (
            AlertVolumePoint,
            AnomalyTrendPoint,
            GeoLocationPoint,
            LoginActivityPoint,
            TopRiskUser,
        )

        now = datetime.utcnow()

        mock_service.get_summary_stats.return_value = DashboardSummary(
            total_logins_24h=1000,
            failed_logins_24h=50,
            active_users_24h=150,
            anomalies_today=10,
            alerts_today=25,
            active_tenants=5,
            avg_risk_score=35.5,
            login_success_rate=95.0,
            top_threats=["impossible_travel"],
        )

        mock_service.get_login_activity_timeline.return_value = LoginActivityTimeline(
            data=[
                LoginActivityPoint(
                    timestamp=now, successful_logins=100, failed_logins=5, total_logins=105
                )
            ],
            time_range=TimeRange.DAY_30,
            total_successful=100,
            total_failed=5,
            change_percent=0.0,
        )

        mock_service.get_geo_heatmap_data.return_value = GeoHeatmapData(
            locations=[
                GeoLocationPoint(
                    country_code="US",
                    country_name="United States",
                    latitude=37.0,
                    longitude=-95.0,
                    login_count=100,
                    user_count=20,
                    risk_score_avg=25.0,
                )
            ],
            total_countries=1,
            top_country="United States",
            top_country_count=100,
        )

        mock_service.get_anomaly_trend.return_value = AnomalyTrendData(
            data=[AnomalyTrendPoint(date=now, count=5, types={"impossible_travel": 5})],
            time_range=TimeRange.DAY_30,
            total_anomalies=5,
            top_type="impossible_travel",
            change_percent=0.0,
        )

        mock_service.get_top_risk_users.return_value = TopRiskUsersData(
            users=[
                TopRiskUser(
                    user_email="test@example.com",
                    tenant_id="tenant-1",
                    risk_score=80,
                    anomaly_count=5,
                    top_anomaly_types=["impossible_travel"],
                    country_count=3,
                )
            ],
            total_users=1,
            avg_risk_score=80.0,
        )

        mock_service.get_alert_volume.return_value = AlertVolumeData(
            data=[AlertVolumePoint(timestamp=now, critical=1, high=2, medium=3, low=4, total=10)],
            time_range=TimeRange.DAY_30,
            total_by_severity={"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4},
            peak_volume=10,
            peak_time=now,
        )

        mock_service.get_anomaly_breakdown.return_value = [
            AnomalyTypeBreakdown(
                type="impossible_travel", count=5, percentage=100.0, avg_risk_score=75.0
            )
        ]

        result = await dashboard_api.get_full_dashboard(
            time_range=TimeRange.DAY_30, tenant_id=None, service=mock_service
        )

        assert isinstance(result, DashboardDataResponse)
        assert result.summary.total_logins_24h == 1000
        assert len(result.login_timeline.data) == 1
        assert len(result.geo_heatmap.locations) == 1
        assert len(result.top_risk_users.users) == 1
        assert result.time_range == TimeRange.DAY_30

        # Verify all service methods were called
        mock_service.get_summary_stats.assert_called_once()
        mock_service.get_login_activity_timeline.assert_called_once()
        mock_service.get_geo_heatmap_data.assert_called_once()
        mock_service.get_anomaly_trend.assert_called_once()
        mock_service.get_top_risk_users.assert_called_once()
        mock_service.get_alert_volume.assert_called_once()
        mock_service.get_anomaly_breakdown.assert_called_once()


class TestExportEndpoint:
    """Test cases for export endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_export_dashboard_success(self, mock_service):
        """Test successful dashboard export request."""
        from src.models.dashboard import ExportRequest

        request = ExportRequest(time_range=TimeRange.DAY_30, format="csv", charts=["all"])

        result = await dashboard_api.export_dashboard(
            request=request, tenant_id=None, service=mock_service
        )

        assert result.format == "csv"
        assert "dashboard-export" in result.filename
        assert result.download_url == "/api/v1/v1/v1/v1/dashboard/export/download/csv"

    @pytest.mark.asyncio
    async def test_export_dashboard_json(self, mock_service):
        """Test dashboard export to JSON."""
        from src.models.dashboard import ExportRequest

        request = ExportRequest(time_range=TimeRange.DAY_7, format="json")

        result = await dashboard_api.export_dashboard(
            request=request, tenant_id="tenant-123", service=mock_service
        )

        assert result.format == "json"
        assert ".json" in result.filename


class TestDownloadExportEndpoint:
    """Test cases for download export endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock dashboard service."""
        service = AsyncMock(spec=DashboardService)
        return service

    @pytest.mark.asyncio
    async def test_download_csv_success(self, mock_service):
        """Test successful CSV download."""
        result = await dashboard_api.download_export(format="csv", service=mock_service)

        assert result.status_code == 200
        assert result.media_type == "text/csv"
        assert "dashboard-export" in result.headers["Content-Disposition"]

    @pytest.mark.asyncio
    async def test_download_json_success(self, mock_service):
        """Test successful JSON download."""
        result = await dashboard_api.download_export(format="json", service=mock_service)

        assert result.status_code == 200
        assert result.media_type == "application/json"

    @pytest.mark.asyncio
    async def test_download_invalid_format(self, mock_service):
        """Test download with invalid format."""
        with pytest.raises(HTTPException) as exc_info:
            await dashboard_api.download_export(format="invalid", service=mock_service)

        assert exc_info.value.status_code == 400
        assert "Unsupported export format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_download_pdf_not_supported(self, mock_service):
        """Test PDF export returns error."""
        with pytest.raises(HTTPException) as exc_info:
            await dashboard_api.download_export(format="pdf", service=mock_service)

        assert exc_info.value.status_code == 400
