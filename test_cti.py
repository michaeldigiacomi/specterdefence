import asyncio
import logging
from datetime import datetime, UTC
import sys

from src.database import async_session_maker
from src.analytics.logins import LoginAnalyticsService

logging.basicConfig(level=logging.INFO)

async def main():
    async with async_session_maker() as session:
        service = LoginAnalyticsService(session)

        # Test with known malicious IP
        user_email = "test.user@digitaladrenalin.net"
        tenant_id = "test-tenant-123"
        malicious_ip = "8.8.8.8"

        print(f"Testing CTI lookup for {malicious_ip}...")

        record = await service.process_login_event(
            user_email=user_email,
            tenant_id=tenant_id,
            ip_address=malicious_ip,
            login_time=datetime.now(UTC),
            is_success=True,
        )

        print("\nResult:")
        print(f"Risk Score: {record.risk_score}")
        print(f"Anomaly Flags: {record.anomaly_flags}")

        if "malicious_ip" in record.anomaly_flags and record.risk_score >= 90:
            print("\nSUCCESS: Malicious IP triggered correctly!")
        else:
            print("\nFAILED: Malicious IP not triggered as expected.")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
