from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.database import get_collection
from app.routes.auth import verify_token

router = APIRouter()

# Pydantic models
class OrderCreate(BaseModel):
    user_id: str
    items: List[str]  # List of menu item IDs
    total_amount: float
    status: str = "pending"
    payment_status: str = "unpaid"
    special_instructions: Optional[str] = None

class OrderItem(BaseModel):
    id: str
    name: str
    price: float
    quantity: int
    size: Optional[str] = None

class CustomerInfo(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    address: str  # عنوان التوصيل مطلوب

class GuestOrderCreate(BaseModel):
    items: List[OrderItem]  # قائمة العناصر مع التفاصيل
    total_amount: float
    customer_info: CustomerInfo
    special_instructions: Optional[str] = None
    payment_method: Optional[str] = "cash"

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    special_instructions: Optional[str] = None

class OrderItemResponse(BaseModel):
    id: str
    name: str
    price: float
    quantity: int

class OrderResponse(BaseModel):
    id: str
    user_id: Optional[str]  # Allow None for guest orders
    items: List[OrderItemResponse]
    total_amount: float
    status: str
    payment_status: str
    customer_info: Optional[CustomerInfo] = None  # Add customer info for guest orders
    special_instructions: Optional[str]
    created_at: datetime
    updated_at: datetime

@router.get("/", response_model=List[OrderResponse])
async def get_orders(status: Optional[str] = None):
    """Get all orders"""
    try:
        orders_collection = await get_collection("orders")
        
        if orders_collection is not None:
            query = {}
            if status:
                query["status"] = status
            cursor = orders_collection.find(query).sort("created_at", -1)
            orders = await cursor.to_list(length=None)
            
            # Convert MongoDB documents to response format
            response_orders = []
            for order in orders:
                # Create customer_info object if exists
                customer_info = None
                if order.get("customer_info"):
                    customer_info = CustomerInfo(**order["customer_info"])
                
                response_orders.append(OrderResponse(
                    id=str(order["_id"]),
                    user_id=order.get("user_id", "guest"),
                    items=order.get("items", []),
                    total_amount=order["total_amount"],
                    status=order["status"],
                    payment_status=order["payment_status"],
                    customer_info=customer_info,
                    special_instructions=order.get("special_instructions"),
                    created_at=order["created_at"],
                    updated_at=order["updated_at"]
                ))
            return response_orders
        else:
            # No database connection - return empty list
            return []
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}"
        )

@router.post("/guest", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_order(order_data: GuestOrderCreate):
    """Create a new order for guest customers (no authentication required)"""
    try:
        orders_collection = await get_collection("orders")

        order_doc = {
            "user_id": None,  # Guest order
            "customer_info": order_data.customer_info.dict(),
            "items": [item.dict() for item in order_data.items],
            "total_amount": order_data.total_amount,
            "status": "pending",
            "payment_status": "unpaid",
            "special_instructions": order_data.special_instructions,
            "payment_method": order_data.payment_method,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if orders_collection is not None:
            result = await orders_collection.insert_one(order_doc)
            order_id = str(result.inserted_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
        return OrderResponse(
            id=order_id,
            user_id="guest",
            items=[],  # Will be populated with actual items
            total_amount=order_data.total_amount,
            status="pending",
            payment_status="unpaid",
            special_instructions=order_data.special_instructions,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create guest order: {str(e)}"
        )

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate, current_user: dict = Depends(verify_token)):
    """Create a new order"""
    try:
        orders_collection = await get_collection("orders")

        order_doc = {
            "user_id": order_data.user_id,
            "items": order_data.items,
            "total_amount": order_data.total_amount,
            "status": order_data.status,
            "payment_status": order_data.payment_status,
            "special_instructions": order_data.special_instructions,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if orders_collection is not None:
            result = await orders_collection.insert_one(order_doc)
            order_id = str(result.inserted_id)
            
            return OrderResponse(
                id=order_id,
                user_id=order_data.user_id,
                items=[],  # Will be populated with actual items
                total_amount=order_data.total_amount,
                status=order_data.status,
                payment_status=order_data.payment_status,
                special_instructions=order_data.special_instructions,
                created_at=order_doc["created_at"],
                updated_at=order_doc["updated_at"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(order_id: str, order_update: OrderUpdate, current_user: dict = Depends(verify_token)):
    """Update an order"""
    try:
        orders_collection = await get_collection("orders")
        
        if orders_collection is not None:
            from bson import ObjectId
            
            update_data = {}
            for field, value in order_update.dict(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = value
            update_data["updated_at"] = datetime.utcnow()

            result = await orders_collection.find_one_and_update(
                {"_id": ObjectId(order_id)},
                {"$set": update_data},
                return_document=True
            )
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found"
                )
            return OrderResponse(
                id=str(result["_id"]),
                user_id=result.get("user_id", "guest"),
                items=result.get("items", []),
                total_amount=result["total_amount"],
                status=result["status"],
                payment_status=result["payment_status"],
                special_instructions=result.get("special_instructions"),
                created_at=result["created_at"],
                updated_at=result["updated_at"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order: {str(e)}"
        )

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(order_id: str, current_user: dict = Depends(verify_token)):
    """Delete an order"""
    try:
        orders_collection = await get_collection("orders")
        
        if orders_collection is not None:
            from bson import ObjectId
            result = await orders_collection.delete_one({"_id": ObjectId(order_id)})
            if result.deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete order: {str(e)}"
        )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """Get a specific order"""
    try:
        orders_collection = await get_collection("orders")
        
        if orders_collection is not None:
            from bson import ObjectId
            order = await orders_collection.find_one({"_id": ObjectId(order_id)})
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found"
                )
            # Create customer_info object if exists
            customer_info = None
            if order.get("customer_info"):
                customer_info = CustomerInfo(**order["customer_info"])
            
            return OrderResponse(
                id=str(order["_id"]),
                user_id=order.get("user_id"),
                items=order.get("items", []),
                total_amount=order["total_amount"],
                status=order["status"],
                payment_status=order["payment_status"],
                customer_info=customer_info,
                special_instructions=order.get("special_instructions"),
                created_at=order["created_at"],
                updated_at=order["updated_at"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order: {str(e)}"
        )

@router.get("/stats")
async def get_order_stats():
    """Get order statistics"""
    try:
        orders_collection = await get_collection("orders")
        
        if orders_collection is not None:
            # Sample aggregation
            total_orders = await orders_collection.count_documents({})
            pending_orders = await orders_collection.count_documents({"status": "pending"})
            
            return {
                "total_orders": total_orders,
                "pending_orders": pending_orders
            }
        else:
            # Development fallback
            total_orders = len(SAMPLE_ORDERS)
            pending_orders = len([order for order in SAMPLE_ORDERS if order["status"] == "pending"])
            
            return {
                "total_orders": total_orders,
                "pending_orders": pending_orders
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order stats: {str(e)}"
        )

