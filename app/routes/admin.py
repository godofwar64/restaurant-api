from fastapi import APIRouter, HTTPException, Depends, status, File, UploadFile, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import uuid
from pathlib import Path
from app.core.database import get_collection
from app.routes.auth import verify_token
from bson import ObjectId

router = APIRouter()

# Pydantic models
class DashboardStats(BaseModel):
    total_users: int
    total_orders: int
    total_customers: int
    total_revenue: float
    new_bookings: int

class AdminUserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(verify_token)):
    """Get admin dashboard statistics"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access dashboard"
        )
    
    try:
        # Get collections
        users_collection = await get_collection("users")
        orders_collection = await get_collection("orders")
        reservations_collection = await get_collection("reservations")
        menu_collection = await get_collection("menu_items")
        
        # Calculate stats
        stats = DashboardStats(
            total_users=0,
            total_orders=0,
            total_customers=0,
            total_revenue=0.0,
            new_bookings=0
        )
        
        if users_collection is not None:
            stats.total_users = await users_collection.count_documents({})
            stats.total_customers = stats.total_users  # Same as total users for now
        
        if orders_collection is not None:
            stats.total_orders = await orders_collection.count_documents({})
            
            # Calculate total revenue from all completed orders
            revenue_cursor = orders_collection.find({
                "payment_status": "paid"
            })
            
            async for order in revenue_cursor:
                stats.total_revenue += order.get("total_amount", 0)
        
        if reservations_collection is not None:
            # Count new bookings (created today)
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            stats.new_bookings = await reservations_collection.count_documents({
                "created_at": {"$gte": today}
            })
        else:
            # Development fallback data
            stats.total_users = 150
            stats.total_orders = 89
            stats.total_customers = 120
            stats.total_revenue = 12750.50
            stats.new_bookings = 8
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard stats: {str(e)}"
        )

@router.get("/users", response_model=List[AdminUserResponse])
async def get_all_users(current_user: dict = Depends(verify_token)):
    """Get all users (Admin only)"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view all users"
        )
    
    try:
        users_collection = await get_collection("users")
        
        if users_collection is not None:
            cursor = users_collection.find({})
            users = await cursor.to_list(length=None)
            
            return [
                AdminUserResponse(
                    id=str(user["_id"]),
                    username=user["username"],
                    email=user["email"],
                    role=user["role"],
                    is_active=user.get("is_active", True),
                    created_at=user["created_at"]
                )
                for user in users
            ]
        else:
            # Development fallback
            return [
                AdminUserResponse(
                    id="dev_admin_id",
                    username="admin",
                    email="admin@restaurantfresh.com",
                    role="admin",
                    is_active=True,
                    created_at=datetime.utcnow()
                )
            ]
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get users: {str(e)}"
        )

@router.put("/users/{user_id}/activate")
async def activate_user(user_id: str, current_user: dict = Depends(verify_token)):
    """Activate a user account (Admin only)"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can activate users"
        )
    
    try:
        users_collection = await get_collection("users")
        
        if users_collection is not None:
            from bson import ObjectId
            
            result = await users_collection.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_active": True, "updated_at": datetime.utcnow()}},
                return_document=True
            )
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return {"message": "User activated successfully", "user_id": user_id}
        else:
            return {"message": "User activated successfully (development mode)", "user_id": user_id}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate user: {str(e)}"
        )

@router.put("/users/{user_id}/deactivate")
async def deactivate_user(user_id: str, current_user: dict = Depends(verify_token)):
    """Deactivate a user account (Admin only)"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can deactivate users"
        )
    
    try:
        users_collection = await get_collection("users")
        
        if users_collection is not None:
            from bson import ObjectId
            
            result = await users_collection.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
                return_document=True
            )
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return {"message": "User deactivated successfully", "user_id": user_id}
        else:
            return {"message": "User deactivated successfully (development mode)", "user_id": user_id}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate user: {str(e)}"
        )

@router.get("/analytics")
async def get_analytics(current_user: dict = Depends(verify_token)):
    """Get restaurant analytics (Admin only)"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access analytics"
        )
    
    try:
        orders_collection = await get_collection("orders")
        
        analytics = {
            "orders_by_status": {},
            "revenue_by_day": {},
            "popular_items": [],
            "customer_stats": {}
        }
        
        if orders_collection is not None:
            # Orders by status
            status_pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            async for doc in orders_collection.aggregate(status_pipeline):
                analytics["orders_by_status"][doc["_id"]] = doc["count"]
            
            # Revenue by day (last 7 days)
            from datetime import timedelta
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            
            revenue_pipeline = [
                {"$match": {"created_at": {"$gte": week_ago}, "payment_status": "paid"}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "revenue": {"$sum": "$total_amount"}
                }}
            ]
            
            async for doc in orders_collection.aggregate(revenue_pipeline):
                analytics["revenue_by_day"][doc["_id"]] = doc["revenue"]
        else:
            # Development fallback
            analytics = {
                "orders_by_status": {"pending": 5, "completed": 20, "cancelled": 2},
                "revenue_by_day": {"2024-01-01": 150.50, "2024-01-02": 200.75},
                "popular_items": ["Margherita Pizza", "Caesar Salad"],
                "customer_stats": {"total_customers": 100, "returning_customers": 60}
            }
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )

# Menu Management Endpoints
class MenuItemRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: str
    image_url: Optional[str] = None
    is_available: Optional[bool] = True
    allergens: Optional[List[str]] = []
    preparation_time: Optional[int] = 15
    prices: Optional[dict] = {}

class MenuItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    category: str
    image_url: Optional[str]
    is_available: bool
    allergens: List[str]
    preparation_time: int
    prices: dict
    created_at: datetime
    updated_at: datetime

@router.post("/upload-image")
async def upload_image(request: Request, file: UploadFile = File(...), current_user: dict = Depends(verify_token)):
    """Upload image file for menu items"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can upload images"
        )
    
    # Check file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, JPG, and WebP images are allowed"
        )
    
    # Check file size (5MB max)
    max_size = 10 * 1024 * 1024  # 5MB
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 5MB"
        )
    
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("static/images/menu")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Build full URL from request
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        image_url = f"{base_url}/static/images/menu/{unique_filename}"
        
        return {
            "message": "Image uploaded successfully",
            "image_url": image_url,
            "filename": unique_filename
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )

@router.post("/menu-items", response_model=MenuItemResponse)
async def add_menu_item(item_data: MenuItemRequest, current_user: dict = Depends(verify_token)):
    """Add new menu item"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can add menu items"
        )
    
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            # Check if item with same name exists
            existing_item = await menu_collection.find_one({"name": item_data.name})
            if existing_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Menu item with this name already exists"
                )
            
            # Create menu item document
            menu_item = {
                "name": item_data.name,
                "description": item_data.description,
                "price": item_data.price,
                "category": item_data.category,
                "image_url": item_data.image_url,
                "is_available": item_data.is_available,
                "allergens": item_data.allergens or [],
                "preparation_time": item_data.preparation_time,
                "prices": item_data.prices or {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await menu_collection.insert_one(menu_item)
            
            return MenuItemResponse(
                id=str(result.inserted_id),
                name=menu_item["name"],
                description=menu_item["description"],
                price=menu_item["price"],
                category=menu_item["category"],
                image_url=menu_item["image_url"],
                is_available=menu_item["is_available"],
                allergens=menu_item["allergens"],
                preparation_time=menu_item["preparation_time"],
                prices=menu_item["prices"],
                created_at=menu_item["created_at"],
                updated_at=menu_item["updated_at"]
            )
        else:
            # Development fallback
            return MenuItemResponse(
                id="dev_item_id",
                name=item_data.name,
                description=item_data.description,
                price=item_data.price,
                category=item_data.category,
                image_url=item_data.image_url,
                is_available=item_data.is_available,
                allergens=item_data.allergens or [],
                preparation_time=item_data.preparation_time,
                prices=item_data.prices or {},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add menu item: {str(e)}"
        )

@router.put("/menu-items/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(item_id: str, item_data: MenuItemRequest, current_user: dict = Depends(verify_token)):
    """Update menu item"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update menu items"
        )
    
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            # Update menu item
            update_data = {
                "name": item_data.name,
                "description": item_data.description,
                "price": item_data.price,
                "category": item_data.category,
                "image_url": item_data.image_url,
                "is_available": item_data.is_available,
                "allergens": item_data.allergens or [],
                "preparation_time": item_data.preparation_time,
                "prices": item_data.prices or {},
                "updated_at": datetime.utcnow()
            }
            
            result = await menu_collection.find_one_and_update(
                {"_id": ObjectId(item_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Menu item not found"
                )
            
            return MenuItemResponse(
                id=str(result["_id"]),
                name=result["name"],
                description=result["description"],
                price=result["price"],
                category=result["category"],
                image_url=result["image_url"],
                is_available=result["is_available"],
                allergens=result["allergens"],
                preparation_time=result["preparation_time"],
                prices=result["prices"],
                created_at=result["created_at"],
                updated_at=result["updated_at"]
            )
        else:
            # Development fallback
            return MenuItemResponse(
                id=item_id,
                name=item_data.name,
                description=item_data.description,
                price=item_data.price,
                category=item_data.category,
                image_url=item_data.image_url,
                is_available=item_data.is_available,
                allergens=item_data.allergens or [],
                preparation_time=item_data.preparation_time,
                prices=item_data.prices or {},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update menu item: {str(e)}"
        )

@router.delete("/menu-items/{item_id}")
async def delete_menu_item(item_id: str, current_user: dict = Depends(verify_token)):
    """Delete menu item"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete menu items"
        )
    
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            result = await menu_collection.find_one_and_delete({"_id": ObjectId(item_id)})
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Menu item not found"
                )
            
            # Optional: Delete associated image file
            if result.get("image_url") and result["image_url"].startswith("/static/"):
                try:
                    image_path = Path(f".{result['image_url']}")
                    if image_path.exists():
                        image_path.unlink()
                except Exception as e:
                    print(f"Failed to delete image file: {e}")
            
            return {"message": "Menu item deleted successfully", "id": item_id}
        else:
            return {"message": "Menu item deleted successfully (development mode)", "id": item_id}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete menu item: {str(e)}"
        )

@router.get("/menu-items", response_model=List[MenuItemResponse])
async def get_all_menu_items(current_user: dict = Depends(verify_token)):
    """Get all menu items for admin"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view all menu items"
        )
    
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            cursor = menu_collection.find({})
            items = await cursor.to_list(length=None)
            
            return [
                MenuItemResponse(
                    id=str(item["_id"]),
                    name=item["name"],
                    description=item.get("description"),
                    price=item["price"],
                    category=item["category"],
                    image_url=item.get("image_url"),
                    is_available=item.get("is_available", True),
                    allergens=item.get("allergens", []),
                    preparation_time=item.get("preparation_time", 15),
                    prices=item.get("prices", {}),
                    created_at=item.get("created_at", datetime.utcnow()),
                    updated_at=item.get("updated_at", datetime.utcnow())
                )
                for item in items
            ]
        else:
            # Development fallback
            return [
                MenuItemResponse(
                    id="dev_item_1",
                    name="Margherita Pizza",
                    description="Classic pizza with tomato sauce and mozzarella",
                    price=45.0,
                    category="Main Course",
                    image_url="/static/images/menu/pizza.jpg",
                    is_available=True,
                    allergens=["dairy", "gluten"],
                    preparation_time=20,
                    prices={"small": 35.0, "medium": 45.0, "large": 55.0},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get menu items: {str(e)}"
        )
