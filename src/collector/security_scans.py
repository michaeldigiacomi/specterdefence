import asyncio
import logging
import sys

# Ensure src is in path
sys.path.insert(0, "/app")

from src.database import async_session_maker, init_db
from src.services.ca_policies import CAPoliciesService
from src.services.mailbox_rules import MailboxRuleService
from src.services.mfa_report import MFAReportService
from src.services.oauth_apps import OAuthAppsService
from src.collector.main import get_active_tenants

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def run_security_scans():
    logger.info("=" * 60)
    logger.info("Starting Heavy Security Scans (MFA, CA, OAuth, Mailbox Rules)")
    logger.info("=" * 60)

    async with async_session_maker() as session:
        try:
            tenants = await get_active_tenants(session)
            logger.info(f"Found {len(tenants)} active tenants for security scans")

            for tenant in tenants:
                try:
                    logger.info(f"Triggering security scans for tenant {tenant.name}...")

                    # MFA Scan
                    mfa_service = MFAReportService(session)
                    await mfa_service.scan_tenant_mfa(tenant.id)
                    logger.info(f"✓ MFA scan completed for {tenant.name}")

                    # CA Policies Scan
                    ca_service = CAPoliciesService(session)
                    await ca_service.scan_tenant_policies(tenant.id)
                    logger.info(f"✓ CA policies scan completed for {tenant.name}")

                    # OAuth Apps Scan
                    oauth_service = OAuthAppsService(session)
                    await oauth_service.scan_tenant_oauth_apps(tenant.id)
                    logger.info(f"✓ OAuth apps scan completed for {tenant.name}")

                    # Mailbox Rules Scan
                    mailbox_service = MailboxRuleService(session)
                    await mailbox_service.scan_tenant_mailbox_rules(tenant.id)
                    logger.info(f"✓ Mailbox rules scan completed for {tenant.name}")

                except Exception as scan_err:
                    logger.error(f"Failed to run security scans for tenant {tenant.name}: {scan_err}")
                
            await session.commit()
        except Exception:
            logger.exception("Unexpected error during security scans")
            await session.rollback()
            raise

async def main() -> int:
    try:
        logger.info("Initializing database...")
        await init_db()

        await run_security_scans()

        return 0
    except Exception as e:
        logger.exception(f"Fatal error in security scans: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
