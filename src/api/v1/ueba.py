"""
UEBA (User and Entity Behavior Analytics) API endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime

from src.ueba.integration import ueba_system

router = APIRouter(prefix="/ueba", tags=["ueba"])

@router.get("/status")
async def get_ueba_status():
    """Get current UEBA system status."""
    try:
        status = ueba_system.get_system_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UEBA status: {str(e)}")

@router.get("/risk-scores")
async def get_risk_scores():
    """Get risk scores for all users."""
    try:
        scores = ueba_system.get_all_risk_scores()
        return {"risk_scores": scores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get risk scores: {str(e)}")

@router.get("/risk-scores/{user_id}")
async def get_user_risk_score(user_id: str):
    """Get risk score for a specific user."""
    try:
        score = ueba_system.get_user_risk_score(user_id)
        return {"user_id": user_id, "risk_score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user risk score: {str(e)}")