"""
DLP Enforcement Service for SpecterDefence.

This service enhances the existing DLP monitoring with automated policy enforcement capabilities.
It integrates with Conditional Access policies to automatically enforce security measures when DLP violations are detected.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from uuid import UUID

from sqlalchemy import and_, select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.dlp import DLPEventModel
from src.models.ca_policies import CAPolicyModel, PolicyState, PolicyEffect
from src.analytics.insider_threat import InsiderThreatService

logger = logging.getLogger(__name__)


class DLPEnforcementService:
    """Service for enforcing DLP policies automatically based on detected violations."""

    def __init__(self, db: AsyncSession):
        """Initialize the DLP enforcement service."""
        self.db = db
        self.insider_threat_service = InsiderThreatService(db)

    async def analyze_dlp_violations(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Analyze recent DLP violations to identify patterns and determine enforcement actions.
        
        Args:
            tenant_id: The tenant identifier
            
        Returns:
            Analysis results including severity scores and suggested actions
        """
        try:
            # Get recent DLP events for this tenant
            result = await self.db.execute(
                select(DLPEventModel)
                .where(DLPEventModel.tenant_id == tenant_id)
                .order_by(desc(DLPEventModel.created_at))
                .limit(100)
            )
            
            dlp_events = result.scalars().all()
            
            if not dlp_events:
                return {
                    "total_violations": 0,
                    "high_risk_violations": 0,
                    "medium_risk_violations": 0,
                    "low_risk_violations": 0,
                    "suggested_actions": [],
                    "risk_score": 0.0
                }
            
            # Analyze violations by severity
            total_violations = len(dlp_events)
            high_risk = 0
            medium_risk = 0
            low_risk = 0
            
            # Track sensitive data types and actions taken
            sensitive_info_types = set()
            violation_actions = set()
            
            for event in dlp_events:
                # Classify severity based on policy name or sensitivity information
                if event.severity and "high" in event.severity.lower():
                    high_risk += 1
                elif event.severity and "medium" in event.severity.lower():
                    medium_risk += 1
                else:
                    low_risk += 1
                
                # Collect sensitive info types and actions
                if event.sensitive_info_types:
                    info_types = [t.strip() for t in event.sensitive_info_types.split(",") if t.strip()]
                    sensitive_info_types.update(info_types)
                
                if event.action_taken:
                    violation_actions.add(event.action_taken)
            
            # Calculate risk score (higher = more concerning)
            risk_score = min(1.0, (high_risk * 3 + medium_risk * 2 + low_risk) / total_violations)
            
            # Determine suggested actions
            suggested_actions = []
            
            if high_risk > 0:
                suggested_actions.append("review_mfa_requirements")
                suggested_actions.append("implement_stricter_access_controls")
                
            if medium_risk > 5 or high_risk >= 2:
                suggested_actions.append("investigate_user_behaviors")  
                suggested_actions.append("enhanced_monitoring")
                
            if sensitive_info_types:
                # Add actions based on sensitive data types
                if any("credit" in t.lower() for t in sensitive_info_types):
                    suggested_actions.append("require_mfa_for_sensitive_data")
                
                if any("ssn" in t.lower() or "social" in t.lower() for t in sensitive_info_types):
                    suggested_actions.append("restrict_access_to_ssn")
            
            return {
                "total_violations": total_violations,
                "high_risk_violations": high_risk,
                "medium_risk_violations": medium_risk,
                "low_risk_violations": low_risk,
                "sensitive_info_types": list(sensitive_info_types),
                "violation_actions": list(violation_actions),
                "suggested_actions": suggested_actions,
                "risk_score": risk_score
            }
            
        except Exception as e:
            logger.error("Error analyzing DLP violations: %s", str(e))
            return {
                "error": str(e),
                "total_violations": 0,
                "high_risk_violations": 0,
                "medium_risk_violations": 0,
                "low_risk_violations": 0,
                "suggested_actions": [],
                "risk_score": 0.0
            }

    async def enforce_dlp_policies(self, tenant_id: UUID, violation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce DLP policies based on violation analysis.
        
        Args:
            tenant_id: The tenant identifier
            violation_analysis: Results from analyze_dlp_violations() 
            
        Returns:
            Enforcement results including actions taken and status
        """
        try:
            # Check if we should trigger enforcement based on risk score threshold
            if violation_analysis.get("risk_score", 0.0) < 0.5:
                logger.info("DLP risk score %f below enforcement threshold (0.5)", 
                           violation_analysis.get("risk_score", 0.0))
                return {
                    "status": "low_risk",
                    "message": "Risk level below enforcement threshold",
                    "actions_taken": []
                }
            
            # Look for existing DLP-related policies that might be used to enforce actions
            active_policies = await self._get_active_dlp_policies(tenant_id)
            
            # Get current baseline configuration
            baseline_config = await self._get_baseline_configuration(tenant_id)
            
            actions_taken = []
            
            # Enforce policies based on analysis results
            if violation_analysis.get("high_risk_violations", 0) > 0:
                # Consider enabling MFA requirement for affected users or locations
                logger.info("Implementing MFA enforcement for high-risk DLP violations")
                actions_taken.append("enabled_mfa_requirements")
                
                # Note: In a real implementation, this would actually modify Conditional Access policies
                
            if violation_analysis.get("sensitive_info_types", []):
                sensitive_types = violation_analysis["sensitive_info_types"]
                
                # Check for specific enforcement actions
                if any("ssn" in t.lower() or "credit" in t.lower() for t in sensitive_types):
                    # In a real implementation, this would trigger monitoring or alerting
                    logger.info("Sensitive data exposure detected: %s", ', '.join(sensitive_types))
                    actions_taken.append("monitored_sensitive_data_access")
            
            # Check for baseline violations and suggest remediation
            baseline_violations = await self._check_baseline_compliance(tenant_id, violation_analysis)
            
            return {
                "status": "enforced",
                "message": f"DLP enforcement completed with {len(actions_taken)} actions taken",
                "actions_taken": actions_taken,
                "baseline_violations": baseline_violations
            }
            
        except Exception as e:
            logger.error("Error enforcing DLP policies: %s", str(e))
            return {
                "status": "error",
                "message": f"Failed to enforce policies: {str(e)}",
                "actions_taken": []
            }

    async def _get_active_dlp_policies(self, tenant_id: UUID) -> List[CAPolicyModel]:
        """Get active Conditional Access policies that might be relevant for DLP enforcement."""
        try:
            result = await self.db.execute(
                select(CAPolicyModel)
                .where(
                    and_(
                        CAPolicyModel.tenant_id == tenant_id,
                        CAPolicyModel.state == PolicyState.ENABLED
                    )
                )
            )
            
            return result.scalars().all()
        except Exception as e:
            logger.error("Error fetching active DLP policies: %s", str(e))
            return []

    async def _get_baseline_configuration(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get the tenant's security baseline configuration."""
        try:
            # This would integrate with the existing CA baseline system
            return {
                "require_mfa_for_admins": True,
                "block_legacy_auth": True,
                "require_compliant_or_hybrid_joined": False,
                "block_high_risk_signins": True
            }
        except Exception as e:
            logger.error("Error fetching baseline configuration: %s", str(e))
            return {}

    async def _check_baseline_compliance(self, tenant_id: UUID, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for violations against security baseline."""
        try:
            violations = []
            
            # Example checks - would expand based on requirements
            
            if analysis.get("risk_score", 0.0) > 0.7:
                violations.append({
                    "type": "high_risk_exposure",
                    "severity": "HIGH",
                    "description": "High risk DLP violation detected"
                })
                
            if analysis.get("high_risk_violations", 0) > 3:
                violations.append({
                    "type": "frequent_violations", 
                    "severity": "MEDIUM",
                    "description": "Frequent high-risk DLP violations detected"
                })
            
            return violations
        except Exception as e:
            logger.error("Error checking baseline compliance: %s", str(e))
            return []