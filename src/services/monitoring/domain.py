"""Domain expiry monitoring service."""

import datetime
from datetime import datetime as dt, timezone
from typing import Optional
import uuid

import whois
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.monitoring import DomainExpiryModel


class DomainExpiryService:
    """Service for monitoring domain expiry."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_domains(
        self,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> list[DomainExpiryModel]:
        """Get all domains for a tenant."""
        query = select(DomainExpiryModel)
        
        if tenant_id:
            query = query.where(DomainExpiryModel.tenant_id == tenant_id)
        
        query = query.order_by(DomainExpiryModel.days_until_expiry)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_domain(
        self,
        domain_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> Optional[DomainExpiryModel]:
        """Get a specific domain."""
        query = select(DomainExpiryModel).where(
            DomainExpiryModel.id == domain_id
        )
        
        if tenant_id:
            query = query.where(DomainExpiryModel.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_expiring_domains(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        days_threshold: int = 30,
    ) -> list[DomainExpiryModel]:
        """Get domains expiring within threshold days."""
        query = select(DomainExpiryModel).where(
            DomainExpiryModel.days_until_expiry <= days_threshold,
            DomainExpiryModel.days_until_expiry >= 0,
        )
        
        if tenant_id:
            query = query.where(DomainExpiryModel.tenant_id == tenant_id)
        
        query = query.order_by(DomainExpiryModel.days_until_expiry)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_domain(
        self,
        tenant_id: uuid.UUID,
        domain: str,
    ) -> DomainExpiryModel:
        """Create a new domain monitor."""
        domain_model = DomainExpiryModel(
            tenant_id=tenant_id,
            domain=domain,
        )
        
        self.db.add(domain_model)
        await self.db.commit()
        await self.db.refresh(domain_model)
        
        return domain_model

    async def delete_domain(
        self,
        domain_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Delete a domain monitor."""
        domain = await self.get_domain(domain_id, tenant_id)
        
        if not domain:
            return False
        
        await self.db.delete(domain)
        await self.db.commit()
        
        return True

    def _check_domain(self, domain: str) -> dict:
        """Check domain WHOIS information."""
        try:
            w = whois.whois(domain)
            
            if not w:
                return {
                    "registrar": None,
                    "registration_date": None,
                    "expiry_date": None,
                    "days_until_expiry": None,
                    "is_expired": True,
                    "whois_error": "No WHOIS data returned",
                }
            
            # Parse dates
            expiry_date = w.expiration_date
            if expiry_date:
                if isinstance(expiry_date, list):
                    expiry_date = expiry_date[0]
                if expiry_date.tzinfo is None:
                    expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                else:
                    expiry_date = expiry_date.astimezone(timezone.utc)
            
            registration_date = w.creation_date
            if registration_date:
                if isinstance(registration_date, list):
                    registration_date = registration_date[0]
                if registration_date.tzinfo is None:
                    registration_date = registration_date.replace(tzinfo=timezone.utc)
                else:
                    registration_date = registration_date.astimezone(timezone.utc)
            
            # Calculate days until expiry
            if expiry_date:
                days_until_expiry = (expiry_date - dt.now(timezone.utc)).days
                is_expired = days_until_expiry < 0
            else:
                days_until_expiry = None
                is_expired = False
            
            # Get registrar
            registrar = None
            if w.registrar:
                if isinstance(w.registrar, list):
                    registrar = w.registrar[0]
                else:
                    registrar = str(w.registrar)
            
            return {
                "registrar": registrar,
                "registration_date": registration_date,
                "expiry_date": expiry_date,
                "days_until_expiry": days_until_expiry,
                "is_expired": is_expired,
                "whois_error": None,
            }
            
        except whois.parser.Py-whoisError as e:
            return {
                "registrar": None,
                "registration_date": None,
                "expiry_date": None,
                "days_until_expiry": None,
                "is_expired": False,
                "whois_error": f"WHOIS parse error: {str(e)}",
            }
        except Exception as e:
            return {
                "registrar": None,
                "registration_date": None,
                "expiry_date": None,
                "days_until_expiry": None,
                "is_expired": False,
                "whois_error": str(e),
            }

    async def check_domain(
        self,
        domain_id: uuid.UUID,
    ) -> Optional[DomainExpiryModel]:
        """Check and update a domain's WHOIS information."""
        domain = await self.get_domain(domain_id)
        
        if not domain:
            return None
        
        result = self._check_domain(domain.domain)
        
        domain.last_checked_at = dt.now(timezone.utc)
        domain.registrar = result["registrar"]
        domain.registration_date = result["registration_date"]
        domain.expiry_date = result["expiry_date"]
        domain.days_until_expiry = result["days_until_expiry"]
        domain.is_expired = result["is_expired"]
        domain.whois_error = result["whois_error"]
        
        await self.db.commit()
        await self.db.refresh(domain)
        
        return domain

    async def check_all_domains(
        self,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> list[DomainExpiryModel]:
        """Check all domains."""
        domains = await self.get_domains(tenant_id)
        
        results = []
        for domain in domains:
            updated = await self.check_domain(domain.id)
            if updated:
                results.append(updated)
        
        return results

    async def get_domain_stats(
        self,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Get aggregated domain stats."""
        domains = await self.get_domains(tenant_id)
        
        total = len(domains)
        active = sum(1 for d in domains if not d.is_expired and not d.whois_error)
        expired = sum(1 for d in domains if d.is_expired)
        expiring_soon = sum(1 for d in domains if d.days_until_expiry and 0 <= d.days_until_expiry <= 30)
        errors = sum(1 for d in domains if d.whois_error)
        
        return {
            "total": total,
            "active": active,
            "expired": expired,
            "expiring_soon": expiring_soon,
            "errors": errors,
        }
