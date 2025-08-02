from datetime import datetime
from typing import Optional, List

class UserModel:
    """User model for MongoDB document structure"""
    
    def __init__(
        self,
        username: str,
        email: str,
        hashed_password: str,
        role: str = "customer",
        full_name: Optional[str] = None,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.role = role
        self.full_name = full_name
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for MongoDB insertion"""
        return {
            "username": self.username,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "role": self.role,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserModel":
        """Create UserModel instance from dictionary"""
        return cls(
            username=data["username"],
            email=data["email"],
            hashed_password=data["hashed_password"],
            role=data.get("role", "customer"),
            full_name=data.get("full_name"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
