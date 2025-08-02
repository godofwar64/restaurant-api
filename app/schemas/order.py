from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OrderItemBase(BaseModel):
    menu_item_id: str
    quantity: int
    price: float
    special_instructions: Optional[str] = None

class OrderItem(OrderItemBase):
    id: str
    name: str

class OrderBase(BaseModel):
    items: List[OrderItemBase]
    special_instructions: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    special_instructions: Optional[str] = None

class Order(BaseModel):
    id: str
    user_id: str
    items: List[OrderItem]
    total_amount: float
    status: str
    payment_status: str
    special_instructions: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderStatus(BaseModel):
    status: str

class PaymentStatus(BaseModel):
    payment_status: str
