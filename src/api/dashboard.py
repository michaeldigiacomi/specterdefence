"""Dashboard API endpoints for security visualizations."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.dashboard import (
    AlertVolumeData,
    AnomalyTrendData,
    AnomalyTypeBreakdown,
    DashboardDataResponse,
    DashboardSummary,
    ExportRequest,
    ExportResponse,
    GeoHeatmapData,
    LoginActivityTimeline,
    TimeRange,
    TopRiskUsersData,
)
from src.services.dashboard import DashboardService

router = APIRouter()
logger = logging.getLogger(__name__)


# ============== Dependencies ==============


async def get_dashboard_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    """Dependency to get dashboard service."""
    return DashboardService(db)


# ============== API Endpoints ==============


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get dashboard summary",
    description="Get summary statistics for the dashboard.",
)
async def get_dashboard_summary(
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    """Get dashboard summary statistics."""
    try:
        return await service.get_summary_stats(tenant_id=tenant_id)
    except Exception as e:
        logger.exception("Error fetching dashboard summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard summary: {str(e)}",
        )


@router.get(
    "/login-timeline",
    response_model=LoginActivityTimeline,
    summary="Get login activity timeline",
    description="Get login activity data over time with success/failed breakdown.",
)
async def get_login_timeline(
    time_range: TimeRange = Query(TimeRange.DAY_30, description="Time range for data"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> LoginActivityTimeline:
    """Get login activity timeline chart data."""
    try:
        return await service.get_login_activity_timeline(time_range=time_range, tenant_id=tenant_id)
    except Exception as e:
        logger.exception("Error fetching login timeline")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching login timeline: {str(e)}",
        )


@router.get(
    "/geo-heatmap",
    response_model=GeoHeatmapData,
    summary="Get geographic heatmap data",
    description="Get login locations aggregated by country for heatmap visualization.",
)
async def get_geo_heatmap(
    time_range: TimeRange = Query(TimeRange.DAY_30, description="Time range for data"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> GeoHeatmapData:
    """Get geographic heatmap data."""
    try:
        return await service.get_geo_heatmap_data(time_range=time_range, tenant_id=tenant_id)
    except Exception as e:
        logger.exception("Error fetching geo heatmap")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching geo heatmap: {str(e)}",
        )


@router.get(
    "/anomaly-trend",
    response_model=AnomalyTrendData,
    summary="Get anomaly trend data",
    description="Get anomaly counts over time with type breakdown.",
)
async def get_anomaly_trend(
    time_range: TimeRange = Query(TimeRange.DAY_30, description="Time range for data"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> AnomalyTrendData:
    """Get anomaly trend chart data."""
    try:
        return await service.get_anomaly_trend(time_range=time_range, tenant_id=tenant_id)
    except Exception as e:
        logger.exception("Error fetching anomaly trend")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching anomaly trend: {str(e)}",
        )


@router.get(
    "/top-risk-users",
    response_model=TopRiskUsersData,
    summary="Get top risk users",
    description="Get list of users with highest risk scores and anomaly counts.",
)
async def get_top_risk_users(
    limit: int = Query(10, ge=1, le=50, description="Number of users to return"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> TopRiskUsersData:
    """Get top risk users list."""
    try:
        return await service.get_top_risk_users(limit=limit, tenant_id=tenant_id)
    except Exception as e:
        logger.exception("Error fetching top risk users")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching top risk users: {str(e)}",
        )


@router.get(
    "/alert-volume",
    response_model=AlertVolumeData,
    summary="Get alert volume data",
    description="Get alert counts by severity over time.",
)
async def get_alert_volume(
    time_range: TimeRange = Query(TimeRange.DAY_30, description="Time range for data"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> AlertVolumeData:
    """Get alert volume chart data."""
    try:
        return await service.get_alert_volume(time_range=time_range, tenant_id=tenant_id)
    except Exception as e:
        logger.exception("Error fetching alert volume")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching alert volume: {str(e)}",
        )


@router.get(
    "/anomaly-breakdown",
    response_model=list[AnomalyTypeBreakdown],
    summary="Get anomaly type breakdown",
    description="Get breakdown of anomalies by type with percentages.",
)
async def get_anomaly_breakdown(
    time_range: TimeRange = Query(TimeRange.DAY_30, description="Time range for data"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[AnomalyTypeBreakdown]:
    """Get anomaly type breakdown."""
    try:
        return await service.get_anomaly_breakdown(time_range=time_range, tenant_id=tenant_id)
    except Exception as e:
        logger.exception("Error fetching anomaly breakdown")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching anomaly breakdown: {str(e)}",
        )


@router.get(
    "/full",
    response_model=DashboardDataResponse,
    summary="Get full dashboard data",
    description="Get all dashboard data in a single request.",
)
async def get_full_dashboard(
    time_range: TimeRange = Query(TimeRange.DAY_30, description="Time range for data"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardDataResponse:
    """Get complete dashboard data."""
    try:
        # Fetch all data concurrently
        summary = await service.get_summary_stats(tenant_id=tenant_id)
        login_timeline = await service.get_login_activity_timeline(
            time_range=time_range, tenant_id=tenant_id
        )
        geo_heatmap = await service.get_geo_heatmap_data(time_range=time_range, tenant_id=tenant_id)
        anomaly_trend = await service.get_anomaly_trend(time_range=time_range, tenant_id=tenant_id)
        top_risk_users = await service.get_top_risk_users(limit=10, tenant_id=tenant_id)
        alert_volume = await service.get_alert_volume(time_range=time_range, tenant_id=tenant_id)
        anomaly_breakdown = await service.get_anomaly_breakdown(
            time_range=time_range, tenant_id=tenant_id
        )

        return DashboardDataResponse(
            summary=summary,
            login_timeline=login_timeline,
            geo_heatmap=geo_heatmap,
            anomaly_trend=anomaly_trend,
            top_risk_users=top_risk_users,
            alert_volume=alert_volume,
            anomaly_breakdown=anomaly_breakdown,
            generated_at=datetime.utcnow(),
            time_range=time_range,
        )
    except Exception as e:
        logger.exception("Error fetching full dashboard data")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard data: {str(e)}",
        )


@router.post(
    "/export",
    response_model=ExportResponse,
    summary="Export dashboard data",
    description="Export dashboard data to PDF, PNG, or CSV.",
)
async def export_dashboard(
    request: ExportRequest,
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    service: DashboardService = Depends(get_dashboard_service),
) -> ExportResponse:
    """Export dashboard data."""
    try:
        # For now, return a mock response
        # Full export implementation would generate actual files
        from datetime import timedelta

        return ExportResponse(
            download_url=f"/api/v1/dashboard/export/download/{request.format}",
            filename=f"dashboard-export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.{request.format}",
            format=request.format,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
    except Exception as e:
        logger.exception("Error exporting dashboard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting dashboard: {str(e)}",
        )


@router.get(
    "/export/download/{format}",
    summary="Download exported dashboard",
    description="Download the exported dashboard file.",
)
async def download_export(
    format: str, service: DashboardService = Depends(get_dashboard_service)
) -> Response:
    """Download exported dashboard file."""
    try:
        # Generate CSV export as default
        if format == "csv":
            # Create CSV data
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            writer.writerow(["Timestamp", "Metric", "Value", "Details"])

            # Write sample data (in real implementation, would use actual data)
            writer.writerow([datetime.utcnow().isoformat(), "Total Logins", "100", "24h"])
            writer.writerow([datetime.utcnow().isoformat(), "Failed Logins", "5", "24h"])
            writer.writerow([datetime.utcnow().isoformat(), "Anomalies", "3", "24h"])

            csv_data = output.getvalue()
            output.close()

            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=dashboard-export-{datetime.utcnow().strftime('%Y%m%d')}.csv"
                },
            )

        elif format == "json":
            import json

            data = {
                "exported_at": datetime.utcnow().isoformat(),
                "format": format,
                "data": {},  # Would contain actual dashboard data
            }

            return Response(
                content=json.dumps(data, indent=2),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=dashboard-export-{datetime.utcnow().strftime('%Y%m%d')}.json"
                },
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}. Use 'csv' or 'json'.",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error downloading export")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading export: {str(e)}",
        )
