"""Dashboard data aggregation service."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import String, and_, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.alerts import AlertHistoryModel
from src.models.analytics import LoginAnalyticsModel
from src.models.dashboard import (
    AlertVolumeData,
    AlertVolumePoint,
    AnomalyTrendData,
    AnomalyTrendPoint,
    AnomalyTypeBreakdown,
    DashboardSummary,
    GeoHeatmapData,
    GeoLocationPoint,
    LoginActivityPoint,
    LoginActivityTimeline,
    TimeRange,
    TopRiskUser,
    TopRiskUsersData,
)
from src.models.mfa_report import MFAUserModel
from src.models.ca_policies import CAPolicyModel, PolicyState
from src.models.oauth_apps import OAuthAppModel, RiskLevel
from src.models.mailbox_rules import MailboxRuleModel, RuleStatus


class DashboardService:
    """Service for aggregating dashboard data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _apply_tenant_filter(self, query: Any, model_class: Any, tenant_id: str | list[str] | None) -> Any:
        if tenant_id is None:
            return query
        if tenant_id == "NONE":
            return query.where(model_class.tenant_id == "NONE_ASSIGNED")
        if isinstance(tenant_id, list):
            return query.where(model_class.tenant_id.in_(tenant_id))
        return query.where(model_class.tenant_id == tenant_id)

    def _get_time_range(self, time_range: TimeRange) -> tuple[datetime, datetime, datetime]:
        """Calculate start and end dates for a time range."""
        end_date = datetime.now(timezone.utc)

        if time_range == TimeRange.DAY_7:
            start_date = end_date - timedelta(days=7)
            prev_start = end_date - timedelta(days=14)
        elif time_range == TimeRange.DAY_30:
            start_date = end_date - timedelta(days=30)
            prev_start = end_date - timedelta(days=60)
        elif time_range == TimeRange.DAY_90:
            start_date = end_date - timedelta(days=90)
            prev_start = end_date - timedelta(days=180)
        else:
            start_date = end_date - timedelta(days=30)
            prev_start = end_date - timedelta(days=60)

        return start_date, end_date, prev_start

    def _get_interval(self, time_range: TimeRange) -> str:
        """Get appropriate time interval for grouping."""
        if time_range == TimeRange.DAY_7:
            return "hour"
        elif time_range == TimeRange.DAY_30:
            return "day"
        else:  # DAY_90
            return "week"

    async def get_login_activity_timeline(
        self, time_range: TimeRange, tenant_id: str | None = None
    ) -> LoginActivityTimeline:
        """Get login activity timeline data."""
        start_date, end_date, prev_start = self._get_time_range(time_range)
        interval = self._get_interval(time_range)

        # Build base query
        query = select(LoginAnalyticsModel).where(
            and_(
                LoginAnalyticsModel.login_time >= start_date,
                LoginAnalyticsModel.login_time <= end_date,
            )
        )

        query = self._apply_tenant_filter(query, LoginAnalyticsModel, tenant_id)

        result = await self.db.execute(query)
        logins = result.scalars().all()

        # Group by time interval
        data_points: dict[datetime, dict[str, int]] = defaultdict(
            lambda: {"success": 0, "failed": 0}
        )

        for login in logins:
            if interval == "hour":
                # Round to hour
                key = login.login_time.replace(minute=0, second=0, microsecond=0)
            elif interval == "day":
                # Round to day
                key = login.login_time.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # week
                # Round to week start (Monday)
                days_since_monday = login.login_time.weekday()
                key = (login.login_time - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            if login.is_success:
                data_points[key]["success"] += 1
            else:
                data_points[key]["failed"] += 1

        # Convert to sorted list
        sorted_points = sorted(data_points.items())

        # Fill in gaps
        filled_data = self._fill_timeline_gaps(sorted_points, start_date, end_date, interval)

        points = [
            LoginActivityPoint(
                timestamp=ts,
                successful_logins=counts["success"],
                failed_logins=counts["failed"],
                total_logins=counts["success"] + counts["failed"],
            )
            for ts, counts in filled_data
        ]

        # Calculate totals
        total_successful = sum(p.successful_logins for p in points)
        total_failed = sum(p.failed_logins for p in points)

        # Get previous period for comparison
        prev_query = select(LoginAnalyticsModel).where(
            and_(
                LoginAnalyticsModel.login_time >= prev_start,
                LoginAnalyticsModel.login_time < start_date,
            )
        )
        prev_query = self._apply_tenant_filter(prev_query, LoginAnalyticsModel, tenant_id)

        prev_result = await self.db.execute(prev_query)
        prev_total = len(prev_result.scalars().all())
        current_total = total_successful + total_failed

        change_percent = 0.0
        if prev_total > 0:
            change_percent = round(float(((current_total - prev_total) / prev_total) * 100), 2)

        return LoginActivityTimeline(
            data=points,
            time_range=time_range,
            total_successful=total_successful,
            total_failed=total_failed,
            change_percent=change_percent,
        )

    def _fill_timeline_gaps(
        self,
        data: list[tuple[datetime, dict[str, int]]],
        start: datetime,
        end: datetime,
        interval: str,
    ) -> list[tuple[datetime, dict[str, int]]]:
        """Fill in missing time intervals with zeros."""
        if not data:
            return []

        filled = []
        current = start
        data_dict = dict(data)

        while current <= end:
            if current in data_dict:
                filled.append((current, data_dict[current]))
            else:
                filled.append((current, {"success": 0, "failed": 0}))

            if interval == "hour":
                current += timedelta(hours=1)
            elif interval == "day":
                current += timedelta(days=1)
            else:  # week
                current += timedelta(weeks=1)

        return filled

    async def get_geo_heatmap_data(
        self, time_range: TimeRange, tenant_id: str | None = None
    ) -> GeoHeatmapData:
        """Get geographic heatmap data."""
        start_date, end_date, _ = self._get_time_range(time_range)

        # Query logins grouped by country
        query = select(
            LoginAnalyticsModel.country_code,
            LoginAnalyticsModel.country,
            LoginAnalyticsModel.latitude,
            LoginAnalyticsModel.longitude,
            func.count(LoginAnalyticsModel.id).label("login_count"),
            func.count(func.distinct(LoginAnalyticsModel.user_email)).label("user_count"),
            func.avg(LoginAnalyticsModel.risk_score).label("avg_risk"),
        ).where(
            and_(
                LoginAnalyticsModel.login_time >= start_date,
                LoginAnalyticsModel.login_time <= end_date,
                LoginAnalyticsModel.country_code.isnot(None),
                LoginAnalyticsModel.latitude.isnot(None),
                LoginAnalyticsModel.longitude.isnot(None),
            )
        )

        query = self._apply_tenant_filter(query, LoginAnalyticsModel, tenant_id)

        query = query.group_by(
            LoginAnalyticsModel.country_code,
            LoginAnalyticsModel.country,
            LoginAnalyticsModel.latitude,
            LoginAnalyticsModel.longitude,
        )

        result = await self.db.execute(query)
        rows = result.all()

        locations = []
        top_country = None
        top_count = 0

        for row in rows:
            if row.country_code and row.latitude and row.longitude:
                locations.append(
                    GeoLocationPoint(
                        country_code=row.country_code.upper(),
                        country_name=row.country or row.country_code,
                        latitude=row.latitude,
                        longitude=row.longitude,
                        login_count=row.login_count,
                        user_count=row.user_count,
                        risk_score_avg=round(float(row.avg_risk or 0), 2),
                    )
                )

                if row.login_count > top_count:
                    top_count = row.login_count
                    top_country = row.country or row.country_code

        return GeoHeatmapData(
            locations=locations,
            total_countries=len(locations),
            top_country=top_country,
            top_country_count=top_count,
        )

    async def get_anomaly_trend(
        self, time_range: TimeRange, tenant_id: str | None = None
    ) -> AnomalyTrendData:
        """Get anomaly trend data."""
        start_date, end_date, prev_start = self._get_time_range(time_range)
        interval = self._get_interval(time_range)

        # Query logins with anomalies
        query = select(LoginAnalyticsModel).where(
            and_(
                LoginAnalyticsModel.login_time >= start_date,
                LoginAnalyticsModel.login_time <= end_date,
                cast(LoginAnalyticsModel.anomaly_flags, String) != '[]',
            )
        )

        query = self._apply_tenant_filter(query, LoginAnalyticsModel, tenant_id)

        result = await self.db.execute(query)
        logins = result.scalars().all()

        # Group by date and anomaly type
        data_points: dict[datetime, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "types": defaultdict(int)}
        )

        type_counts: dict[str, int] = defaultdict(int)

        for login in logins:
            if interval == "hour":
                key = login.login_time.replace(minute=0, second=0, microsecond=0)
            elif interval == "day":
                key = login.login_time.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                days_since_monday = login.login_time.weekday()
                key = (login.login_time - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            data_points[key]["count"] += 1

            for flag in login.anomaly_flags:
                data_points[key]["types"][flag] += 1
                type_counts[flag] += 1

        # Fill gaps
        sorted_points = sorted(data_points.items())
        filled_data = self._fill_anomaly_gaps(sorted_points, start_date, end_date, interval)

        points = [
            AnomalyTrendPoint(date=ts, count=data["count"], types=dict(data["types"]))
            for ts, data in filled_data
        ]

        total_anomalies = sum(p.count for p in points)
        top_type = max(type_counts.keys(), key=lambda x: type_counts[x]) if type_counts else None

        # Calculate change percent
        prev_query = select(LoginAnalyticsModel).where(
            and_(
                LoginAnalyticsModel.login_time >= prev_start,
                LoginAnalyticsModel.login_time < start_date,
                cast(LoginAnalyticsModel.anomaly_flags, String) != '[]',
            )
        )
        prev_query = self._apply_tenant_filter(prev_query, LoginAnalyticsModel, tenant_id)

        prev_result = await self.db.execute(prev_query)
        prev_count = len(prev_result.scalars().all())

        change_percent = 0.0
        if prev_count > 0:
            change_percent = round(float(((total_anomalies - prev_count) / prev_count) * 100), 2)

        return AnomalyTrendData(
            data=points,
            time_range=time_range,
            total_anomalies=total_anomalies,
            top_type=top_type,
            change_percent=change_percent,
        )

    def _fill_anomaly_gaps(
        self,
        data: list[tuple[datetime, dict[str, Any]]],
        start: datetime,
        end: datetime,
        interval: str,
    ) -> list[tuple[datetime, dict[str, Any]]]:
        """Fill in missing time intervals with zeros for anomalies."""
        if not data:
            return []

        filled = []
        current = start
        data_dict = dict(data)

        while current <= end:
            if current in data_dict:
                filled.append((current, data_dict[current]))
            else:
                filled.append((current, {"count": 0, "types": {}}))

            if interval == "hour":
                current += timedelta(hours=1)
            elif interval == "day":
                current += timedelta(days=1)
            else:
                current += timedelta(weeks=1)

        return filled

    async def get_top_risk_users(
        self, limit: int = 10, tenant_id: str | None = None
    ) -> TopRiskUsersData:
        """Get top risk users."""
        # Query users with highest risk scores
        query = select(
            LoginAnalyticsModel.user_email,
            LoginAnalyticsModel.tenant_id,
            func.max(LoginAnalyticsModel.risk_score).label("max_risk"),
            func.count(LoginAnalyticsModel.id).label("anomaly_count"),
            func.max(LoginAnalyticsModel.login_time).label("last_anomaly"),
        ).where(cast(LoginAnalyticsModel.anomaly_flags, String) != '[]')

        query = self._apply_tenant_filter(query, LoginAnalyticsModel, tenant_id)

        query = (
            query.group_by(LoginAnalyticsModel.user_email, LoginAnalyticsModel.tenant_id)
            .order_by(desc("max_risk"))
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        users = []
        total_risk = 0

        for row in rows:
            # Get top anomaly types for this user
            types_query = (
                select(LoginAnalyticsModel.anomaly_flags)
                .where(LoginAnalyticsModel.user_email == row.user_email)
            )

            types_result = await self.db.execute(types_query)
            
            unique_types = set()
            for (flags,) in types_result:
                if flags:
                    unique_types.update(flags)
            
            # Convert set to list for JSON serialization
            anomaly_types = list(unique_types)

            # Get unique country count
            country_query = select(
                func.count(func.distinct(LoginAnalyticsModel.country_code))
            ).where(LoginAnalyticsModel.user_email == row.user_email)
            country_result = await self.db.execute(country_query)
            country_count = country_result.scalar() or 0

            users.append(
                TopRiskUser(
                    user_email=row.user_email,
                    tenant_id=row.tenant_id,
                    risk_score=row.max_risk,
                    anomaly_count=row.anomaly_count,
                    last_anomaly_time=row.last_anomaly,
                    top_anomaly_types=anomaly_types[:5],
                    country_count=country_count,
                )
            )

            total_risk += row.max_risk

        avg_risk = round(float(total_risk / len(users)), 2) if users else 0.0

        return TopRiskUsersData(users=users, total_users=len(users), avg_risk_score=avg_risk)

    async def get_alert_volume(
        self, time_range: TimeRange, tenant_id: str | None = None
    ) -> AlertVolumeData:
        """Get alert volume data by severity."""
        start_date, end_date, _ = self._get_time_range(time_range)
        interval = self._get_interval(time_range)

        # Query alerts grouped by time and severity
        query = select(AlertHistoryModel.sent_at, AlertHistoryModel.severity).where(
            and_(AlertHistoryModel.sent_at >= start_date, AlertHistoryModel.sent_at <= end_date)
        )

        query = self._apply_tenant_filter(query, AlertHistoryModel, tenant_id)

        result = await self.db.execute(query)
        alerts = result.all()

        # Group by time interval
        data_points: dict[datetime, dict[str, int]] = defaultdict(
            lambda: {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0}
        )

        peak_volume = 0
        peak_time = None

        for alert in alerts:
            if interval == "hour":
                key = alert.sent_at.replace(minute=0, second=0, microsecond=0)
            elif interval == "day":
                key = alert.sent_at.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                days_since_monday = alert.sent_at.weekday()
                key = (alert.sent_at - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            severity = (
                alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
            )
            data_points[key][severity] += 1
            data_points[key]["total"] += 1

            if data_points[key]["total"] > peak_volume:
                peak_volume = data_points[key]["total"]
                peak_time = key

        # Fill gaps
        sorted_points = sorted(data_points.items())
        filled_data = self._fill_alert_gaps(sorted_points, start_date, end_date, interval)

        points = [
            AlertVolumePoint(
                timestamp=ts,
                critical=counts["CRITICAL"],
                high=counts["HIGH"],
                medium=counts["MEDIUM"],
                low=counts["LOW"],
                total=counts["total"],
            )
            for ts, counts in filled_data
        ]

        # Calculate totals by severity
        total_by_severity = {
            "CRITICAL": sum(p.critical for p in points),
            "HIGH": sum(p.high for p in points),
            "MEDIUM": sum(p.medium for p in points),
            "LOW": sum(p.low for p in points),
        }

        return AlertVolumeData(
            data=points,
            time_range=time_range,
            total_by_severity=total_by_severity,
            peak_volume=peak_volume,
            peak_time=peak_time,
        )

    def _fill_alert_gaps(
        self,
        data: list[tuple[datetime, dict[str, int]]],
        start: datetime,
        end: datetime,
        interval: str,
    ) -> list[tuple[datetime, dict[str, int]]]:
        """Fill in missing time intervals with zeros for alerts."""
        if not data:
            return []

        filled = []
        current = start
        data_dict = dict(data)

        while current <= end:
            if current in data_dict:
                filled.append((current, data_dict[current]))
            else:
                filled.append(
                    (current, {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0})
                )

            if interval == "hour":
                current += timedelta(hours=1)
            elif interval == "day":
                current += timedelta(days=1)
            else:
                current += timedelta(weeks=1)

        return filled

    async def get_anomaly_breakdown(
        self, time_range: TimeRange, tenant_id: str | None = None
    ) -> list[AnomalyTypeBreakdown]:
        """Get breakdown of anomalies by type."""
        start_date, end_date, _ = self._get_time_range(time_range)

        # Query all anomalies
        query = select(LoginAnalyticsModel.anomaly_flags, LoginAnalyticsModel.risk_score).where(
            and_(
                LoginAnalyticsModel.login_time >= start_date,
                LoginAnalyticsModel.login_time <= end_date,
                cast(LoginAnalyticsModel.anomaly_flags, String) != '[]',
            )
        )

        query = self._apply_tenant_filter(query, LoginAnalyticsModel, tenant_id)

        result = await self.db.execute(query)
        rows = result.all()

        # Aggregate by type
        type_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "risk_sum": 0})

        total_count = 0

        for row in rows:
            for flag in row.anomaly_flags:
                type_stats[flag]["count"] += 1
                type_stats[flag]["risk_sum"] += row.risk_score
                total_count += 1

        breakdown = []
        for anomaly_type, stats in sorted(
            type_stats.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            percentage = round(float((stats["count"] / total_count) * 100), 2) if total_count > 0 else 0
            avg_risk = round(float(stats["risk_sum"] / stats["count"]), 2) if stats["count"] > 0 else 0

            breakdown.append(
                AnomalyTypeBreakdown(
                    type=anomaly_type,
                    count=stats["count"],
                    percentage=percentage,
                    avg_risk_score=avg_risk,
                )
            )

        return breakdown

    async def get_summary_stats(self, tenant_id: str | None = None) -> DashboardSummary:
        """Get dashboard summary statistics."""
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Login stats (24h)
        login_query = select(LoginAnalyticsModel).where(LoginAnalyticsModel.login_time >= day_ago)
        login_query = self._apply_tenant_filter(login_query, LoginAnalyticsModel, tenant_id)

        login_result = await self.db.execute(login_query)
        logins = login_result.scalars().all()

        total_logins = len(logins)
        failed_logins = sum(1 for login in logins if not login.is_success)
        active_users = len({login.user_email for login in logins})

        # Anomalies today
        anomaly_query = select(LoginAnalyticsModel).where(
            and_(
                LoginAnalyticsModel.login_time >= today_start,
                cast(LoginAnalyticsModel.anomaly_flags, String) != '[]',
            )
        )
        anomaly_query = self._apply_tenant_filter(anomaly_query, LoginAnalyticsModel, tenant_id)

        anomaly_result = await self.db.execute(anomaly_query)
        anomaly_logins = anomaly_result.scalars().all()
        anomalies_today = len(anomaly_logins)

        # Alerts today
        alert_query = select(AlertHistoryModel).where(AlertHistoryModel.sent_at >= today_start)
        alert_query = self._apply_tenant_filter(alert_query, AlertHistoryModel, tenant_id)

        alert_result = await self.db.execute(alert_query)
        alerts_today = len(alert_result.scalars().all())

        # Active tenants
        from src.models.db import TenantModel

        tenant_query = select(TenantModel).where(TenantModel.is_active)
        tenant_result = await self.db.execute(tenant_query)
        active_tenants = len(tenant_result.scalars().all())

        # Average risk score
        risk_query = select(func.avg(LoginAnalyticsModel.risk_score)).where(
            LoginAnalyticsModel.login_time >= day_ago
        )
        risk_query = self._apply_tenant_filter(risk_query, LoginAnalyticsModel, tenant_id)

        risk_result = await self.db.execute(risk_query)
        avg_risk = risk_result.scalar() or 0

        # Login success rate
        success_rate = (
            ((total_logins - failed_logins) / total_logins * 100) if total_logins > 0 else 100
        )

        # Top threats (anomaly types today)
        threat_types: dict[str, int] = defaultdict(int)
        for login in anomaly_logins:
            for flag in login.anomaly_flags:
                threat_types[flag] += 1

        top_threats = sorted(threat_types.keys(), key=lambda x: threat_types[x], reverse=True)[:3]

        # Posture metrics
        mfa_query = select(MFAUserModel)
        mfa_query = self._apply_tenant_filter(mfa_query, MFAUserModel, tenant_id)
        mfa_result = await self.db.execute(mfa_query)
        mfa_users = mfa_result.scalars().all()
        
        total_protected_users = len(mfa_users)
        mfa_registered = sum(1 for u in mfa_users if u.is_mfa_registered)
        mfa_compliance_rate = (mfa_registered / total_protected_users * 100) if total_protected_users > 0 else 0.0

        oauth_query = select(func.count(OAuthAppModel.id)).where(
            OAuthAppModel.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
        )
        oauth_query = self._apply_tenant_filter(oauth_query, OAuthAppModel, tenant_id)
        oauth_result = await self.db.execute(oauth_query)
        high_risk_oauth_apps = oauth_result.scalar() or 0

        ca_query = select(func.count(CAPolicyModel.id)).where(
            CAPolicyModel.state == PolicyState.DISABLED
        )
        ca_query = self._apply_tenant_filter(ca_query, CAPolicyModel, tenant_id)
        ca_result = await self.db.execute(ca_query)
        disabled_ca_policies = ca_result.scalar() or 0

        rule_query = select(func.count(MailboxRuleModel.id)).where(
            MailboxRuleModel.status.in_([RuleStatus.SUSPICIOUS, RuleStatus.MALICIOUS])
        )
        rule_query = self._apply_tenant_filter(rule_query, MailboxRuleModel, tenant_id)
        rule_result = await self.db.execute(rule_query)
        suspicious_mailbox_rules = rule_result.scalar() or 0

        return DashboardSummary(
            total_logins_24h=total_logins,
            failed_logins_24h=failed_logins,
            active_users_24h=active_users,
            anomalies_today=anomalies_today,
            alerts_today=alerts_today,
            active_tenants=active_tenants,
            avg_risk_score=round(float(avg_risk), 2),
            login_success_rate=round(float(success_rate), 2),
            anomalies_per_user=round(float(anomalies_today / active_users) if active_users > 0 else 0, 2),
            mfa_compliance_rate=round(float(mfa_compliance_rate), 2),
            high_risk_oauth_apps=high_risk_oauth_apps,
            disabled_ca_policies=disabled_ca_policies,
            suspicious_mailbox_rules=suspicious_mailbox_rules,
            total_protected_users=total_protected_users,
        )
