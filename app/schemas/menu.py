from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class MenuItemBase(BaseModel):
    name: str
    description: str
    price: float
    category: str
    image_url: Optional[str] = None
    is_available: Optional[bool] = True
    allergens: Optional[List[str]] = []
    preparation_time: Optional[int] = 15  # minutes
    prices: Optional[Dict[str, float]] = {}  # أسعار الأحجام المختلفة
    popular: Optional[bool] = False

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    allergens: Optional[List[str]] = None
    preparation_time: Optional[int] = None
    prices: Optional[Dict[str, float]] = None
    popular: Optional[bool] = None

class MenuItem(MenuItemBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CategoryResponse(BaseModel):
    categories: List[str]
