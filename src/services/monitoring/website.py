"""Website monitoring service."""

from datetime import datetime, timezone
from typing import Optional
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.monitoring import WebsiteMonitorModel


class WebsiteMonitorService:
    """Service for monitoring website availability."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_websites(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        include_disabled: bool = False,
    ) -> list[WebsiteMonitorModel]:
        """Get all website monitors for a tenant."""
        query = select(WebsiteMonitorModel)
        
        if tenant_id:
            query = query.where(WebsiteMonitorModel.tenant_id == tenant_id)
        
        if not include_disabled:
            query = query.where(WebsiteMonitorModel.is_enabled == True)
        
        query = query.order_by(WebsiteMonitorModel.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_website(
        self,
        website_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> Optional[WebsiteMonitorModel]:
        """Get a specific website monitor."""
        query = select(WebsiteMonitorModel).where(
            WebsiteMonitorModel.id == website_id
        )
        
        if tenant_id:
            query = query.where(WebsiteMonitorModel.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_website(
        self,
        tenant_id: uuid.UUID,
        name: str,
        url: str,
        check_interval_minutes: int = 5,
    ) -> WebsiteMonitorModel:
        """Create a new website monitor."""
        website = WebsiteMonitorModel(
            tenant_id=tenant_id,
            name=name,
            url=url,
            check_interval_minutes=check_interval_minutes,
        )
        
        self.db.add(website)
        await self.db.commit()
        await self.db.refresh(website)
        
        return website

    async def update_website(
        self,
        website_id: uuid.UUID,
        tenant_id: uuid.UUID,
        **updates,
    ) -> Optional[WebsiteMonitorModel]:
        """Update a website monitor."""
        website = await self.get_website(website_id, tenant_id)
        
        if not website:
            return None
        
        for key, value in updates.items():
            if hasattr(website, key):
                setattr(website, key, value)
        
        website.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(website)
        
        return website

    async def delete_website(
        self,
        website_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Delete a website monitor."""
        website = await self.get_website(website_id, tenant_id)
        
        if not website:
            return False
        
        await self.db.delete(website)
        await self.db.commit()
        
        return True

    async def check_website(self, website: WebsiteMonitorModel) -> dict:
        """Check website availability."""
        start_time = datetime.now(timezone.utc)
        
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
            ) as client:
                response = await client.get(website.url)
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    status = "up"
                else:
                    status = "down"
                
                return {
                    "status": status,
                    "response_code": response.status_code,
                    "response_time_ms": response_time,
                    "error": None,
                }
                
        except httpx.TimeoutException:
            return {
                "status": "down",
                "response_code": None,
                "response_time_ms": None,
                "error": "Timeout",
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "response_code": None,
                "response_time_ms": None,
                "error": str(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "response_code": None,
                "response_time_ms": None,
                "error": str(e),
            }

    async def run_check(self, website_id: uuid.UUID) -> Optional[WebsiteMonitorModel]:
        """Run a check for a specific website and update its status."""
        website = await self.get_website(website_id)
        
        if not website:
            return None
        
        result = await self.check_website(website)
        
        website.last_checked_at = datetime.now(timezone.utc)
        website.last_status = result["status"]
        website.last_response_code = result["response_code"]
        website.last_response_time_ms = result["response_time_ms"]
        website.last_error = result["error"]
        website.total_checks += 1
        
        if result["status"] == "up":
            website.successful_checks += 1
        
        # Calculate uptime percentage
        if website.total_checks > 0:
            website.uptime_percentage = (website.successful_checks / website.total_checks) * 100
        
        website.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(website)
        
        return website

    async def check_all_websites(self, tenant_id: Optional[uuid.UUID] = None) -> list[WebsiteMonitorModel]:
        """Check all enabled websites."""
        websites = await self.get_websites(tenant_id, include_disabled=False)
        
        results = []
        for website in websites:
            if website.is_enabled:
                updated = await self.run_check(website.id)
                if updated:
                    results.append(updated)
        
        return results

    async def get_website_stats(
        self,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Get aggregated website stats."""
        websites = await self.get_websites(tenant_id)
        
        total = len(websites)
        up = sum(1 for w in websites if w.last_status == "up")
        down = sum(1 for w in websites if w.last_status == "down")
        error = sum(1 for w in websites if w.last_status == "error")
        unknown = sum(1 for w in websites if w.last_status is None)
        
        avg_uptime = 0
        if websites:
            avg_uptime = sum(w.uptime_percentage for w in websites) / len(websites)
        
        return {
            "total": total,
            "up": up,
            "down": down,
            "error": error,
            "unknown": unknown,
            "average_uptime": round(avg_uptime, 2),
        }
