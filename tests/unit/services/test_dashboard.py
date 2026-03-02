"""Unit tests for dashboard service."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.alerts import SeverityLevel
from src.models.analytics import LoginAnalyticsModel
from src.models.dashboard import (
    TimeRange,
)
from src.services.dashboard import DashboardService


@pytest.fixture
def frozen_time():
    """Return a fixed datetime for testing."""
    return datetime(2026, 3, 2, 12, 0, 0)


class TestDashboardServiceTimeRanges:
    """Test cases for time range calculations."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    def test_get_time_range_7d(self, service):
        """Test 7-day time range calculation."""
        start, end, prev_start = service._get_time_range(TimeRange.DAY_7)

        assert (end - start).days == 7
        assert (start - prev_start).days == 7

    def test_get_time_range_30d(self, service):
        """Test 30-day time range calculation."""
        start, end, prev_start = service._get_time_range(TimeRange.DAY_30)

        assert (end - start).days == 30
        assert (start - prev_start).days == 30

    def test_get_time_range_90d(self, service):
        """Test 90-day time range calculation."""
        start, end, prev_start = service._get_time_range(TimeRange.DAY_90)

        assert (end - start).days == 90
        assert (start - prev_start).days == 90

    def test_get_interval_7d(self, service):
        """Test interval for 7-day range."""
        assert service._get_interval(TimeRange.DAY_7) == "hour"

    def test_get_interval_30d(self, service):
        """Test interval for 30-day range."""
        assert service._get_interval(TimeRange.DAY_30) == "day"

    def test_get_interval_90d(self, service):
        """Test interval for 90-day range."""
        assert service._get_interval(TimeRange.DAY_90) == "week"


class TestDashboardServiceLoginTimeline:
    """Test cases for login timeline aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    @pytest.mark.asyncio
    async def test_get_login_activity_timeline_success(self, service, mock_db):
        """Test successful login timeline aggregation."""
        now = datetime.utcnow()

        # Create mock logins
        mock_login1 = MagicMock(spec=LoginAnalyticsModel)
        mock_login1.login_time = now - timedelta(hours=1)
        mock_login1.is_success = True
        mock_login1.user_email = "user1@example.com"

        mock_login2 = MagicMock(spec=LoginAnalyticsModel)
        mock_login2.login_time = now
        mock_login2.is_success = False
        mock_login2.user_email = "user2@example.com"

        # Mock the execute results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_login1, mock_login2]
        mock_db.execute.return_value = mock_result

        result = await service.get_login_activity_timeline(TimeRange.DAY_7)

        assert isinstance(result.data, list)
        assert result.time_range == TimeRange.DAY_7
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_login_activity_timeline_with_tenant(self, service, mock_db):
        """Test login timeline with tenant filter."""
        tenant_id = str(uuid4())

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_login_activity_timeline(
            TimeRange.DAY_30,
            tenant_id=tenant_id
        )

        assert result.total_successful == 0
        assert result.total_failed == 0


class TestDashboardServiceGeoHeatmap:
    """Test cases for geo heatmap aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    @pytest.mark.asyncio
    async def test_get_geo_heatmap_data_success(self, service, mock_db):
        """Test successful geo heatmap aggregation."""
        # Create mock result rows
        mock_row = MagicMock()
        mock_row.country_code = "US"
        mock_row.country = "United States"
        mock_row.latitude = 37.0902
        mock_row.longitude = -95.7129
        mock_row.login_count = 100
        mock_row.user_count = 20
        mock_row.avg_risk = 25.5

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        result = await service.get_geo_heatmap_data(TimeRange.DAY_30)

        assert len(result.locations) == 1
        assert result.locations[0].country_code == "US"
        assert result.total_countries == 1
        assert result.top_country == "United States"

    @pytest.mark.asyncio
    async def test_get_geo_heatmap_data_empty(self, service, mock_db):
        """Test geo heatmap with no data."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_geo_heatmap_data(TimeRange.DAY_7)

        assert len(result.locations) == 0
        assert result.total_countries == 0
        assert result.top_country is None

    @pytest.mark.asyncio
    async def test_get_geo_heatmap_multiple_countries(self, service, mock_db):
        """Test geo heatmap with multiple countries."""
        mock_rows = [
            MagicMock(
                country_code="US",
                country="United States",
                latitude=37.0,
                longitude=-95.0,
                login_count=500,
                user_count=100,
                avg_risk=25.0
            ),
            MagicMock(
                country_code="GB",
                country="United Kingdom",
                latitude=55.0,
                longitude=-3.0,
                login_count=200,
                user_count=50,
                avg_risk=30.0
            ),
            MagicMock(
                country_code="DE",
                country="Germany",
                latitude=51.0,
                longitude=10.0,
                login_count=300,
                user_count=75,
                avg_risk=28.0
            )
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        result = await service.get_geo_heatmap_data(TimeRange.DAY_30)

        assert len(result.locations) == 3
        assert result.total_countries == 3
        assert result.top_country == "United States"
        assert result.top_country_count == 500


class TestDashboardServiceAnomalyTrend:
    """Test cases for anomaly trend aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    @pytest.mark.asyncio
    async def test_get_anomaly_trend_success(self, service, mock_db, frozen_time):
        """Test successful anomaly trend aggregation."""
        with patch('src.services.dashboard.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = frozen_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            mock_login = MagicMock(spec=LoginAnalyticsModel)
            mock_login.login_time = frozen_time
            mock_login.anomaly_flags = ["impossible_travel", "new_country"]
            mock_login.user_email = "user@example.com"
            mock_login.tenant_id = "tenant-1"

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_login]
            mock_db.execute.return_value = mock_result

            result = await service.get_anomaly_trend(TimeRange.DAY_7)

            assert isinstance(result.data, list)
            assert result.total_anomalies >= 1
            assert result.time_range == TimeRange.DAY_7

    @pytest.mark.asyncio
    async def test_get_anomaly_trend_top_type(self, service, mock_db, frozen_time):
        """Test anomaly trend correctly identifies top type."""
        with patch('src.services.dashboard.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = frozen_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Create multiple logins with different anomaly types
            mock_logins = [
                MagicMock(
                    login_time=frozen_time - timedelta(hours=i),
                    anomaly_flags=["impossible_travel"],
                    user_email=f"user{i}@example.com",
                    tenant_id="tenant-1"
                )
                for i in range(5)
            ] + [
                MagicMock(
                    login_time=frozen_time - timedelta(hours=i),
                    anomaly_flags=["new_country"],
                    user_email=f"user{i+5}@example.com",
                    tenant_id="tenant-1"
                )
                for i in range(2)
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_logins
            mock_db.execute.return_value = mock_result

            result = await service.get_anomaly_trend(TimeRange.DAY_7)

            assert result.top_type == "impossible_travel"
            assert result.total_anomalies == 7


class TestDashboardServiceTopRiskUsers:
    """Test cases for top risk users aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    @pytest.mark.asyncio
    async def test_get_top_risk_users_success(self, service, mock_db):
        """Test successful top risk users retrieval."""
        now = datetime.utcnow()

        mock_row = MagicMock()
        mock_row.user_email = "highrisk@example.com"
        mock_row.tenant_id = "tenant-1"
        mock_row.max_risk = 95
        mock_row.anomaly_count = 15
        mock_row.last_anomaly = now

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]

        # Mock the different queries
        async def mock_execute(query):
            if "distinct" in str(query).lower():
                # Types query
                types_result = MagicMock()
                types_result.all.return_value = [("impossible_travel",), ("new_country",)]
                return types_result
            elif "count" in str(query).lower() and "country_code" in str(query):
                # Country count query
                country_result = MagicMock()
                country_result.scalar.return_value = 5
                return country_result
            else:
                # Main query
                return mock_result

        mock_db.execute.side_effect = mock_execute

        result = await service.get_top_risk_users(limit=10)

        assert len(result.users) == 1
        assert result.users[0].user_email == "highrisk@example.com"
        assert result.users[0].risk_score == 95

    @pytest.mark.asyncio
    async def test_get_top_risk_users_sorted_by_risk(self, service, mock_db):
        """Test that users are sorted by risk score."""
        mock_rows = [
            MagicMock(
                user_email="high@example.com",
                tenant_id="tenant-1",
                max_risk=95,
                anomaly_count=20,
                last_anomaly=datetime.utcnow()
            ),
            MagicMock(
                user_email="medium@example.com",
                tenant_id="tenant-1",
                max_risk=70,
                anomaly_count=10,
                last_anomaly=datetime.utcnow()
            ),
            MagicMock(
                user_email="low@example.com",
                tenant_id="tenant-1",
                max_risk=50,
                anomaly_count=5,
                last_anomaly=datetime.utcnow()
            )
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows

        async def mock_execute(query):
            if "distinct" in str(query).lower():
                types_result = MagicMock()
                types_result.all.return_value = []
                return types_result
            elif "country_code" in str(query).lower():
                country_result = MagicMock()
                country_result.scalar.return_value = 1
                return country_result
            else:
                return mock_result

        mock_db.execute.side_effect = mock_execute

        result = await service.get_top_risk_users(limit=10)

        assert len(result.users) == 3
        assert result.users[0].risk_score == 95  # Highest first
        assert result.users[1].risk_score == 70
        assert result.users[2].risk_score == 50
        assert round(result.avg_risk_score, 2) == round((95 + 70 + 50) / 3, 2)


class TestDashboardServiceAlertVolume:
    """Test cases for alert volume aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    @pytest.mark.asyncio
    async def test_get_alert_volume_success(self, service, mock_db, frozen_time):
        """Test successful alert volume aggregation."""
        with patch('src.services.dashboard.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = frozen_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            mock_alert = MagicMock()
            mock_alert.sent_at = frozen_time
            mock_alert.severity = SeverityLevel.HIGH

            mock_result = MagicMock()
            mock_result.all.return_value = [mock_alert]
            mock_db.execute.return_value = mock_result

            result = await service.get_alert_volume(TimeRange.DAY_7)

            assert isinstance(result.data, list)
            assert result.total_by_severity["HIGH"] >= 1
            assert result.time_range == TimeRange.DAY_7

    @pytest.mark.asyncio
    async def test_get_alert_volume_peak_detection(self, service, mock_db, frozen_time):
        """Test that peak volume is correctly identified."""
        with patch('src.services.dashboard.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = frozen_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            mock_alerts = [
                MagicMock(sent_at=frozen_time - timedelta(days=2), severity=SeverityLevel.CRITICAL),
                MagicMock(sent_at=frozen_time - timedelta(days=2), severity=SeverityLevel.HIGH),
                MagicMock(sent_at=frozen_time - timedelta(days=2), severity=SeverityLevel.HIGH),
                MagicMock(sent_at=frozen_time - timedelta(days=1), severity=SeverityLevel.MEDIUM),
            ]

            mock_result = MagicMock()
            mock_result.all.return_value = mock_alerts
            mock_db.execute.return_value = mock_result

            result = await service.get_alert_volume(TimeRange.DAY_7)

            assert result.peak_volume == 3  # 2 days ago had 3 alerts


class TestDashboardServiceAnomalyBreakdown:
    """Test cases for anomaly breakdown aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    @pytest.mark.asyncio
    async def test_get_anomaly_breakdown_success(self, service, mock_db):
        """Test successful anomaly breakdown aggregation."""
        mock_row = MagicMock()
        mock_row.anomaly_flags = ["impossible_travel", "new_country"]
        mock_row.risk_score = 75

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        result = await service.get_anomaly_breakdown(TimeRange.DAY_30)

        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_anomaly_breakdown_percentages(self, service, mock_db):
        """Test that percentages are calculated correctly."""
        mock_rows = [
            MagicMock(anomaly_flags=["impossible_travel"], risk_score=80),
            MagicMock(anomaly_flags=["impossible_travel"], risk_score=90),
            MagicMock(anomaly_flags=["new_country"], risk_score=60),
            MagicMock(anomaly_flags=["new_country"], risk_score=70),
            MagicMock(anomaly_flags=["new_country"], risk_score=50),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        result = await service.get_anomaly_breakdown(TimeRange.DAY_30)

        # Should have 2 types: impossible_travel and new_country
        assert len(result) == 2

        # Find the types
        impossible_travel = next((r for r in result if r.type == "impossible_travel"), None)
        new_country = next((r for r in result if r.type == "new_country"), None)

        assert impossible_travel is not None
        assert impossible_travel.count == 2
        assert impossible_travel.percentage == 40.0
        assert impossible_travel.avg_risk_score == 85.0

        assert new_country is not None
        assert new_country.count == 3
        assert new_country.percentage == 60.0
        assert new_country.avg_risk_score == 60.0


class TestDashboardServiceSummary:
    """Test cases for dashboard summary statistics."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    @pytest.mark.asyncio
    async def test_get_summary_stats_success(self, service, mock_db, frozen_time):
        """Test successful summary stats retrieval."""
        with patch('src.services.dashboard.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = frozen_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            mock_datetime.timedelta = timedelta

            # Mock logins
            mock_logins = [
                MagicMock(
                    user_email="user1@example.com",
                    is_success=True,
                    risk_score=25,
                    anomaly_flags=[]
                ),
                MagicMock(
                    user_email="user2@example.com",
                    is_success=False,
                    risk_score=50,
                    anomaly_flags=["failed_login"]
                ),
            ]

            # Mock alerts
            mock_alerts = [
                MagicMock(sent_at=frozen_time),
                MagicMock(sent_at=frozen_time),
            ]

            # Mock tenants
            mock_tenants = [
                MagicMock(is_active=True),
                MagicMock(is_active=False),
                MagicMock(is_active=True),
            ]

            async def mock_execute(query):
                mock_result = MagicMock()
                query_str = str(query).lower()

                if "anomaly_flags" in query_str and "today" in str(query):
                    mock_result.scalars.return_value.all.return_value = [mock_logins[1]]
                elif "alert_history" in query_str or "sent_at" in query_str:
                    mock_result.scalars.return_value.all.return_value = mock_alerts
                elif "tenants" in query_str and "is_active" in query_str:
                    # Return only active tenants
                    active_tenants = [t for t in mock_tenants if t.is_active]
                    mock_result.scalars.return_value.all.return_value = active_tenants
                elif "tenants" in query_str:
                    mock_result.scalars.return_value.all.return_value = mock_tenants
                elif "avg" in query_str and "risk_score" in query_str:
                    mock_result.scalar.return_value = 37.5
                else:
                    mock_result.scalars.return_value.all.return_value = mock_logins

                return mock_result

            mock_db.execute.side_effect = mock_execute

            result = await service.get_summary_stats()

            assert result.total_logins_24h == 2
            assert result.failed_logins_24h == 1
            assert result.active_users_24h == 2
            assert result.alerts_today == 2
            assert result.active_tenants == 2
            assert result.login_success_rate == 50.0

    @pytest.mark.asyncio
    async def test_get_summary_stats_with_tenant(self, service, mock_db):
        """Test summary stats with tenant filter."""
        tenant_id = str(uuid4())

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_summary_stats(tenant_id=tenant_id)

        assert result.total_logins_24h == 0
        assert result.active_tenants == 0


class TestDashboardServiceFillGaps:
    """Test cases for timeline gap filling."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create a dashboard service instance."""
        return DashboardService(mock_db)

    def test_fill_timeline_gaps_hourly(self, service):
        """Test filling hourly gaps in timeline."""
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 3, 0, 0)

        data = [
            (datetime(2024, 1, 1, 0, 0, 0), {"success": 10, "failed": 1}),
            (datetime(2024, 1, 1, 2, 0, 0), {"success": 20, "failed": 2}),
        ]

        result = service._fill_timeline_gaps(data, start, end, "hour")

        assert len(result) == 4  # 00:00, 01:00, 02:00, 03:00
        assert result[0][1]["success"] == 10
        assert result[1][1]["success"] == 0  # Filled gap
        assert result[2][1]["success"] == 20
        assert result[3][1]["success"] == 0  # Filled gap

    def test_fill_timeline_gaps_daily(self, service):
        """Test filling daily gaps in timeline."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 5)

        data = [
            (datetime(2024, 1, 1), {"success": 100, "failed": 10}),
            (datetime(2024, 1, 3), {"success": 150, "failed": 15}),
        ]

        result = service._fill_timeline_gaps(data, start, end, "day")

        assert len(result) == 5
        assert result[0][1]["success"] == 100
        assert result[1][1]["success"] == 0  # Jan 2
        assert result[2][1]["success"] == 150
        assert result[3][1]["success"] == 0  # Jan 4
        assert result[4][1]["success"] == 0  # Jan 5

    def test_fill_timeline_gaps_empty(self, service):
        """Test filling gaps with empty data."""
        result = service._fill_timeline_gaps(
            [],
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            "day"
        )

        assert result == []
