# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    notes: Optional[str] = None
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserPasswordChange(BaseModel):
    new_password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    is_active: bool
    role: UserRole
    created_at: datetime

    class Config:
        orm_mode = True


class UserListItem(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    is_active: bool
    role: UserRole
    created_at: datetime

    class Config:
        orm_mode = True


class UserListResponse(BaseModel):
    users: List[UserListItem]
    total_count: int


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None
