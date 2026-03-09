"""Users API endpoints."""

from typing import List, Any
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.user import UserModel
from src.models.db import TenantModel
from src.api.auth_local import require_admin, get_current_user, get_password_hash

router = APIRouter()

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    is_admin: bool = False

class UserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = Field(None, min_length=8)

class UserResponse(BaseModel):
    id: Any
    username: str
    is_active: bool
    is_admin: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TenantLightResponse(BaseModel):
    id: Any
    name: str

    class Config:
        from_attributes = True

@router.get("/", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """List all users (Admin only)."""
    result = await db.execute(select(UserModel).order_by(UserModel.username))
    return result.scalars().all()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Create a new user (Admin only)."""
    # Check if user exists
    result = await db.execute(select(UserModel).where(UserModel.username == user_in.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = UserModel(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        is_active=True,
        is_admin=user_in.is_admin
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Update a user (Admin only)."""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.is_active is not None:
        db_user.is_active = user_in.is_active
    if user_in.is_admin is not None:
        db_user.is_admin = user_in.is_admin
    if user_in.password:
        db_user.password_hash = get_password_hash(user_in.password)

    db_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/{user_id}/tenants", response_model=List[TenantLightResponse])
async def get_user_tenants(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get tenants assigned to a user."""
    # Only admins can view other users' tenants
    if not user.get("is_admin") and user.get("id") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.tenants)).where(UserModel.id == user_id)
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return db_user.tenants

@router.post("/{user_id}/tenants/{tenant_id}")
async def assign_tenant(
    user_id: int,
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Assign a tenant to a user (Admin only)."""
    # Check user
    user_res = await db.execute(select(UserModel).options(selectinload(UserModel.tenants)).where(UserModel.id == user_id))
    db_user = user_res.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check tenant
    tenant_res = await db.execute(select(TenantModel).where(TenantModel.id == tenant_id))
    db_tenant = tenant_res.scalar_one_or_none()
    if not db_tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if any(t.id == db_tenant.id for t in db_user.tenants):
        return {"message": "Tenant already assigned"}

    db_user.tenants.append(db_tenant)
    await db.commit()
    return {"message": "Tenant assigned successfully"}

@router.delete("/{user_id}/tenants/{tenant_id}")
async def unassign_tenant(
    user_id: int,
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Unassign a tenant from a user (Admin only)."""
    user_res = await db.execute(select(UserModel).options(selectinload(UserModel.tenants)).where(UserModel.id == user_id))
    db_user = user_res.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find the tenant object in user.tenants
    tenant_to_remove = None
    for t in db_user.tenants:
        if str(t.id) == tenant_id:
            tenant_to_remove = t
            break

    if not tenant_to_remove:
        return {"message": "Tenant not assigned to user"}

    db_user.tenants.remove(tenant_to_remove)
    await db.commit()
    return {"message": "Tenant unassigned successfully"}
