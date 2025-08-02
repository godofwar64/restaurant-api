from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from app.core.database import get_collection
from app.routes.auth import verify_token

router = APIRouter()

# Pydantic models
class MenuItem(BaseModel):
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

class MenuItemResponse(BaseModel):
    id: str
    name: str
    description: str
    price: float
    category: str
    image_url: Optional[str] = None
    is_available: bool
    allergens: List[str]
    preparation_time: int
    prices: Optional[Dict[str, float]] = {}
    popular: Optional[bool] = False
    created_at: datetime
    updated_at: datetime

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

# Sample menu data for development
SAMPLE_MENU = [
    {
        "id": "1",
        "name": "Margherita Pizza",
        "description": "Classic pizza with tomato sauce, mozzarella, and fresh basil",
        "price": 12.99,
        "category": "Pizza",
        "image_url": "/uploads/margherita.jpg",
        "is_available": True,
        "allergens": ["Gluten", "Dairy"],
        "preparation_time": 20,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "id": "2",
        "name": "Caesar Salad",
        "description": "Fresh romaine lettuce, parmesan cheese, croutons, and Caesar dressing",
        "price": 8.99,
        "category": "Salads",
        "image_url": "/uploads/caesar-salad.jpg",
        "is_available": True,
        "allergens": ["Dairy", "Eggs"],
        "preparation_time": 10,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "id": "3",
        "name": "Grilled Salmon",
        "description": "Fresh Atlantic salmon grilled to perfection with herbs and lemon",
        "price": 18.99,
        "category": "Main Course",
        "image_url": "/uploads/grilled-salmon.jpg",
        "is_available": True,
        "allergens": ["Fish"],
        "preparation_time": 25,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]

@router.get("/", response_model=List[MenuItemResponse])
async def get_menu(category: Optional[str] = None, available_only: bool = True):
    """Get all menu items"""
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            # Build query
            query = {}
            if category:
                query["category"] = category
            if available_only:
                query["is_available"] = True
            
            # Get items from database
            cursor = menu_collection.find(query)
            items = await cursor.to_list(length=None)
            
            # Convert to response format
            menu_items = []
            for item in items:
                menu_items.append(MenuItemResponse(
                    id=str(item["_id"]),
                    name=item["name"],
                    description=item["description"],
                    price=item["price"],
                    category=item["category"],
                    image_url=item.get("image_url"),
                    is_available=item["is_available"],
                    allergens=item.get("allergens", []),
                    preparation_time=item.get("preparation_time", 15),
                    prices=item.get("prices", {}),
                    popular=item.get("popular", False),
                    created_at=item["created_at"],
                    updated_at=item["updated_at"]
                ))
            
            return menu_items
        else:
            # Return sample data for development
            filtered_menu = SAMPLE_MENU.copy()
            if category:
                filtered_menu = [item for item in filtered_menu if item["category"] == category]
            if available_only:
                filtered_menu = [item for item in filtered_menu if item["is_available"]]
            
            return [MenuItemResponse(**item) for item in filtered_menu]
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get menu items: {str(e)}"
        )

@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(item_id: str):
    """Get a specific menu item"""
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            from bson import ObjectId
            try:
                item = await menu_collection.find_one({"_id": ObjectId(item_id)})
            except:
                item = None
            
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Menu item not found"
                )
            
            return MenuItemResponse(
                id=str(item["_id"]),
                name=item["name"],
                description=item["description"],
                price=item["price"],
                category=item["category"],
                image_url=item.get("image_url"),
                is_available=item["is_available"],
                allergens=item.get("allergens", []),
                preparation_time=item.get("preparation_time", 15),
                prices=item.get("prices", {}),
                popular=item.get("popular", False),
                created_at=item["created_at"],
                updated_at=item["updated_at"]
            )
        else:
            # Find in sample data
            for item in SAMPLE_MENU:
                if item["id"] == item_id:
                    return MenuItemResponse(**item)
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get menu item: {str(e)}"
        )

@router.post("/", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(item: MenuItem, current_user: dict = Depends(verify_token)):
    """Create a new menu item (Admin only)"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create menu items"
        )
    
    try:
        menu_collection = await get_collection("menu_items")
        
        # Create menu item document
        now = datetime.utcnow()
        item_doc = {
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "category": item.category,
            "image_url": item.image_url,
            "is_available": item.is_available,
            "allergens": item.allergens or [],
            "preparation_time": item.preparation_time or 15,
            "prices": item.prices or {},
            "popular": item.popular or False,
            "created_at": now,
            "updated_at": now
        }
        
        if menu_collection is not None:
            # Insert into database
            result = await menu_collection.insert_one(item_doc)
            item_id = str(result.inserted_id)
        else:
            # Development fallback
            item_id = f"dev_{len(SAMPLE_MENU) + 1}"
            item_doc["id"] = item_id
            SAMPLE_MENU.append(item_doc)
        
        return MenuItemResponse(
            id=item_id,
            **item_doc
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create menu item: {str(e)}"
        )

@router.put("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(item_id: str, item_update: MenuItemUpdate, current_user: dict = Depends(verify_token)):
    """Update a menu item (Admin only)"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update menu items"
        )
    
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            from bson import ObjectId
            
            # Prepare update data
            update_data = {}
            for field, value in item_update.dict(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = value
            
            if update_data:
                update_data["updated_at"] = datetime.utcnow()
                
                # Update in database
                try:
                    result = await menu_collection.find_one_and_update(
                        {"_id": ObjectId(item_id)},
                        {"$set": update_data},
                        return_document=True
                    )
                except:
                    result = None
                
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
                    image_url=result.get("image_url"),
                    is_available=result["is_available"],
                    allergens=result.get("allergens", []),
                    preparation_time=result.get("preparation_time", 15),
                    prices=result.get("prices", {}),
                    popular=result.get("popular", False),
                    created_at=result["created_at"],
                    updated_at=result["updated_at"]
                )
        else:
            # Development fallback
            for i, item in enumerate(SAMPLE_MENU):
                if item["id"] == item_id:
                    for field, value in item_update.dict(exclude_unset=True).items():
                        if value is not None:
                            SAMPLE_MENU[i][field] = value
                    SAMPLE_MENU[i]["updated_at"] = datetime.utcnow()
                    return MenuItemResponse(**SAMPLE_MENU[i])
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update menu item: {str(e)}"
        )

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(item_id: str, current_user: dict = Depends(verify_token)):
    """Delete a menu item (Admin only)"""
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete menu items"
        )
    
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            from bson import ObjectId
            
            try:
                result = await menu_collection.delete_one({"_id": ObjectId(item_id)})
            except:
                result = None
            
            if not result or result.deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Menu item not found"
                )
        else:
            # Development fallback
            for i, item in enumerate(SAMPLE_MENU):
                if item["id"] == item_id:
                    SAMPLE_MENU.pop(i)
                    return
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete menu item: {str(e)}"
        )

@router.get("/categories/list")
async def get_categories():
    """Get all menu categories"""
    try:
        menu_collection = await get_collection("menu_items")
        
        if menu_collection is not None:
            # Get distinct categories from database
            categories = await menu_collection.distinct("category")
            return {"categories": categories}
        else:
            # Development fallback
            categories = list(set(item["category"] for item in SAMPLE_MENU))
            return {"categories": categories}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {str(e)}"
        )
