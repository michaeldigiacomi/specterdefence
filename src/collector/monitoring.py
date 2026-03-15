"""Monitoring collector - runs periodic checks for websites, SSL, and domains."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import async_session_maker
from src.models.monitoring import WebsiteMonitorModel, SslCertificateModel, DomainExpiryModel

logger = logging.getLogger(__name__)


class MonitoringCollector:
    """Collector for monitoring checks."""

    def __init__(self):
        self.db: Optional[AsyncSession] = None

    async def __aenter__(self):
        self.db = async_session_maker()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            await self.db.close()

    async def check_all_websites(self, tenant_id: Optional[uuid.UUID] = None):
        """Check all enabled websites."""
        from src.services.monitoring.website import WebsiteMonitorService
        
        query = select(WebsiteMonitorModel).where(
            WebsiteMonitorModel.is_enabled == True
        )
        
        if tenant_id:
            query = query.where(WebsiteMonitorModel.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        websites = list(result.scalars().all())
        
        service = WebsiteMonitorService(self.db)
        
        for website in websites:
            try:
                await service.run_check(website.id)
                logger.info(f"Checked website: {website.name} ({website.url})")
            except Exception as e:
                logger.error(f"Failed to check website {website.name}: {e}")
        
        return len(websites)

    async def check_all_ssl_certificates(self, tenant_id: Optional[uuid.UUID] = None):
        """Check all SSL certificates."""
        from src.services.monitoring.ssl import SslCertificateService
        
        query = select(SslCertificateModel)
        
        if tenant_id:
            query = query.where(SslCertificateModel.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        certificates = list(result.scalars().all())
        
        service = SslCertificateService(self.db)
        
        for cert in certificates:
            try:
                await service.check_certificate(cert.id)
                logger.info(f"Checked SSL certificate: {cert.domain}")
            except Exception as e:
                logger.error(f"Failed to check SSL certificate {cert.domain}: {e}")
        
        return len(certificates)

    async def check_all_domains(self, tenant_id: Optional[uuid.UUID] = None):
        """Check all domains."""
        from src.services.monitoring.domain import DomainExpiryService
        
        query = select(DomainExpiryModel)
        
        if tenant_id:
            query = query.where(DomainExpiryModel.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        domains = list(result.scalars().all())
        
        service = DomainExpiryService(self.db)
        
        for domain in domains:
            try:
                await service.check_domain(domain.id)
                logger.info(f"Checked domain: {domain.domain}")
            except Exception as e:
                logger.error(f"Failed to check domain {domain.domain}: {e}")
        
        return len(domains)

    async def run_all_checks(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        check_websites: bool = True,
        check_ssl: bool = True,
        check_domains: bool = True,
    ) -> dict:
        """Run all monitoring checks."""
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "websites": {"checked": 0},
            "ssl": {"checked": 0},
            "domains": {"checked": 0},
        }
        
        if check_websites:
            results["websites"]["checked"] = await self.check_all_websites(tenant_id)
        
        if check_ssl:
            results["ssl"]["checked"] = await self.check_all_ssl_certificates(tenant_id)
        
        if check_domains:
            results["domains"]["checked"] = await self.check_all_domains(tenant_id)
        
        return results


async def run_monitoring_checks(
    check_websites: bool = True,
    check_ssl: bool = True,
    check_domains: bool = True,
) -> dict:
    """Run all monitoring checks (standalone function)."""
    async with MonitoringCollector() as collector:
        return await collector.run_all_checks(
            check_websites=check_websites,
            check_ssl=check_ssl,
            check_domains=check_domains,
        )


if __name__ == "__main__":
    # This can be run as a standalone script or as a k8s cron job
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Parse arguments
    check_websites = "--no-websites" not in sys.argv
    check_ssl = "--no-ssl" not in sys.argv
    check_domains = "--no-domains" not in sys.argv
    
    result = asyncio.run(run_monitoring_checks(
        check_websites=check_websites,
        check_ssl=check_ssl,
        check_domains=check_domains,
    ))
    
    print(f"Monitoring check results: {result}")
