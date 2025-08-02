from datetime import datetime
from typing import Optional, List, Dict

class MenuItemModel:
    """Menu item model for MongoDB document structure"""
    
    def __init__(
        self,
        name: str,
        description: str,
        price: float,
        category: str,
        image_url: Optional[str] = None,
        is_available: bool = True,
        allergens: Optional[List[str]] = None,
        preparation_time: int = 15,
        prices: Optional[Dict[str, float]] = None,
        popular: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.image_url = image_url
        self.is_available = is_available
        self.allergens = allergens or []
        self.preparation_time = preparation_time
        self.prices = prices or {}
        self.popular = popular
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for MongoDB insertion"""
        return {
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "category": self.category,
            "image_url": self.image_url,
            "is_available": self.is_available,
            "allergens": self.allergens,
            "preparation_time": self.preparation_time,
            "prices": self.prices,
            "popular": self.popular,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MenuItemModel":
        """Create MenuItemModel instance from dictionary"""
        return cls(
            name=data["name"],
            description=data["description"],
            price=data["price"],
            category=data["category"],
            image_url=data.get("image_url"),
            is_available=data.get("is_available", True),
            allergens=data.get("allergens", []),
            preparation_time=data.get("preparation_time", 15),
            prices=data.get("prices", {}),
            popular=data.get("popular", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
