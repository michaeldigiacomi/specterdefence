"""SSL certificate monitoring service."""

import asyncio
import datetime
from datetime import datetime as dt, timezone
import ssl
import socket
from typing import Optional
import uuid

from cryptography import x509
from cryptography.hazmat.backends import default_backend
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.monitoring import SslCertificateModel


class SslCertificateService:
    """Service for monitoring SSL certificates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_certificates(
        self,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> list[SslCertificateModel]:
        """Get all SSL certificates for a tenant."""
        query = select(SslCertificateModel)
        
        if tenant_id:
            query = query.where(SslCertificateModel.tenant_id == tenant_id)
        
        query = query.order_by(SslCertificateModel.days_until_expiry)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_certificate(
        self,
        certificate_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> Optional[SslCertificateModel]:
        """Get a specific SSL certificate."""
        query = select(SslCertificateModel).where(
            SslCertificateModel.id == certificate_id
        )
        
        if tenant_id:
            query = query.where(SslCertificateModel.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_expiring_certificates(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        days_threshold: int = 30,
    ) -> list[SslCertificateModel]:
        """Get certificates expiring within threshold days."""
        query = select(SslCertificateModel).where(
            SslCertificateModel.days_until_expiry <= days_threshold,
            SslCertificateModel.days_until_expiry >= 0,
        )
        
        if tenant_id:
            query = query.where(SslCertificateModel.tenant_id == tenant_id)
        
        query = query.order_by(SslCertificateModel.days_until_expiry)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_certificate(
        self,
        tenant_id: uuid.UUID,
        domain: str,
        port: int = 443,
    ) -> SslCertificateModel:
        """Create a new SSL certificate monitor."""
        certificate = SslCertificateModel(
            tenant_id=tenant_id,
            domain=domain,
            port=port,
        )
        
        self.db.add(certificate)
        await self.db.commit()
        await self.db.refresh(certificate)
        
        return certificate

    async def delete_certificate(
        self,
        certificate_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Delete an SSL certificate monitor."""
        certificate = await self.get_certificate(certificate_id, tenant_id)
        
        if not certificate:
            return False
        
        await self.db.delete(certificate)
        await self.db.commit()
        
        return True

    def _get_certificate(self, domain: str, port: int = 443) -> dict:
        """Get SSL certificate details from a domain."""
        try:
            context = ssl.create_default_context()
            
            with socket.create_connection((domain, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    x509_cert = x509.load_der_x509_certificate(cert, default_backend())
                    
                    # Extract certificate details
                    issuer = ", ".join(
                        attr.rstrip(" ") for attr in x509_cert.issuer.rdn_as_attributes()
                    )
                    subject = ", ".join(
                        attr.rstrip(" ") for attr in x509_cert.subject.rdn_as_attributes()
                    )
                    valid_from = x509_cert.not_valid_before_utc.replace(tzinfo=timezone.utc)
                    valid_until = x509_cert.not_valid_after_utc.replace(tzinfo=timezone.utc)
                    days_until_expiry = (valid_until - dt.now(timezone.utc)).days
                    serial = format(x509_cert.serial_number, 'x')
                    sig_alg = x509_cert.signature_algorithm_oid._name
                    
                    is_valid = days_until_expiry > 0
                    
                    return {
                        "issuer": issuer,
                        "subject": subject,
                        "valid_from": valid_from,
                        "valid_until": valid_until,
                        "days_until_expiry": days_until_expiry,
                        "serial_number": serial,
                        "signature_algorithm": sig_alg,
                        "is_valid": is_valid,
                        "has_errors": False,
                        "error_message": None,
                    }
                    
        except socket.timeout:
            return {
                "issuer": None,
                "subject": None,
                "valid_from": None,
                "valid_until": None,
                "days_until_expiry": None,
                "serial_number": None,
                "signature_algorithm": None,
                "is_valid": False,
                "has_errors": True,
                "error_message": "Connection timeout",
            }
        except socket.gaierror as e:
            return {
                "issuer": None,
                "subject": None,
                "valid_from": None,
                "valid_until": None,
                "days_until_expiry": None,
                "serial_number": None,
                "signature_algorithm": None,
                "is_valid": False,
                "has_errors": True,
                "error_message": f"DNS error: {str(e)}",
            }
        except ssl.SSLError as e:
            return {
                "issuer": None,
                "subject": None,
                "valid_from": None,
                "valid_until": None,
                "days_until_expiry": None,
                "serial_number": None,
                "signature_algorithm": None,
                "is_valid": False,
                "has_errors": True,
                "error_message": f"SSL error: {str(e)}",
            }
        except Exception as e:
            return {
                "issuer": None,
                "subject": None,
                "valid_from": None,
                "valid_until": None,
                "days_until_expiry": None,
                "serial_number": None,
                "signature_algorithm": None,
                "is_valid": False,
                "has_errors": True,
                "error_message": str(e),
            }

    async def check_certificate(
        self,
        certificate_id: uuid.UUID,
    ) -> Optional[SslCertificateModel]:
        """Check and update an SSL certificate."""
        certificate = await self.get_certificate(certificate_id)
        
        if not certificate:
            return None
        
        result = self._get_certificate(certificate.domain, certificate.port)
        
        certificate.last_checked_at = dt.now(timezone.utc)
        certificate.issuer = result["issuer"]
        certificate.subject = result["subject"]
        certificate.valid_from = result["valid_from"]
        certificate.valid_until = result["valid_until"]
        certificate.days_until_expiry = result["days_until_expiry"]
        certificate.serial_number = result["serial_number"]
        certificate.signature_algorithm = result["signature_algorithm"]
        certificate.is_valid = result["is_valid"]
        certificate.has_errors = result["has_errors"]
        certificate.error_message = result["error_message"]
        
        await self.db.commit()
        await self.db.refresh(certificate)
        
        return certificate

    async def check_all_certificates(
        self,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> list[SslCertificateModel]:
        """Check all SSL certificates."""
        certificates = await self.get_certificates(tenant_id)
        
        results = []
        for cert in certificates:
            updated = await self.check_certificate(cert.id)
            if updated:
                results.append(updated)
        
        return results

    async def get_certificate_stats(
        self,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Get aggregated SSL certificate stats."""
        certificates = await self.get_certificates(tenant_id)
        
        total = len(certificates)
        valid = sum(1 for c in certificates if c.is_valid and not c.has_errors)
        expired = sum(1 for c in certificates if c.is_expired)
        expiring_soon = sum(1 for c in certificates if c.days_until_expiry and 0 <= c.days_until_expiry <= 30)
        errors = sum(1 for c in certificates if c.has_errors)
        
        return {
            "total": total,
            "valid": valid,
            "expired": expired,
            "expiring_soon": expiring_soon,
            "errors": errors,
        }
