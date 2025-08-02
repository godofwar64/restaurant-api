from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.database import get_collection
from app.routes.auth import verify_token

router = APIRouter()

# Pydantic models
class ReservationCreate(BaseModel):
    customerName: str
    customerPhone: str
    customerEmail: str
    date: str  # يوم-شهر-سنة
    time: str  # الوقت
    guests: int  # عدد الأشخاص
    special_requests: Optional[str] = None  # تعليمات إضافية

class ReservationResponse(BaseModel):
    id: str
    customerName: str
    customerPhone: str
    customerEmail: str
    date: str
    time: str
    guests: int
    status: str
    special_requests: Optional[str]
    created_at: datetime
    updated_at: datetime

class ReservationUpdate(BaseModel):
    status: Optional[str] = None
    special_requests: Optional[str] = None
    customerName: Optional[str] = None
    customerPhone: Optional[str] = None
    customerEmail: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    guests: Optional[int] = None

# Sample reservations data for development
SAMPLE_RESERVATIONS = [
    {
        "id": "1",
        "customerName": "أحمد محمد",
        "customerPhone": "01234567890",
        "customerEmail": "ahmed@example.com",
        "date": "2024-08-15",
        "time": "19:00",
        "guests": 4,
        "status": "pending",
        "special_requests": "عشاء عيد ميلاد، يرجى تحضير كعكة",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "id": "2",
        "customerName": "فاطمة علي",
        "customerPhone": "01098765432",
        "customerEmail": "fatima@example.com",
        "date": "2024-08-16",
        "time": "20:30",
        "guests": 2,
        "status": "confirmed",
        "special_requests": "طاولة هادئة بجانب النافذة",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "id": "3",
        "customerName": "محمد حسن",
        "customerPhone": "01123456789",
        "customerEmail": "mohammed@example.com",
        "date": "2024-08-17",
        "time": "18:00",
        "guests": 6,
        "status": "pending",
        "special_requests": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "id": "4",
        "customerName": "سارة إبراهيم",
        "customerPhone": "01187654321",
        "customerEmail": "sara@example.com",
        "date": "2024-08-18",
        "time": "21:00",
        "guests": 3,
        "status": "cancelled",
        "special_requests": "عشاء رومانسي",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]

@router.get("/", response_model=List[ReservationResponse])
async def get_reservations(status: Optional[str] = None):
    """Get all reservations"""
    try:
        reservations_collection = await get_collection("reservations")
        
        if reservations_collection is not None:
            query = {}
            if status:
                query["status"] = status
            cursor = reservations_collection.find(query)
            reservations = await cursor.to_list(length=None)
            
            # Convert MongoDB documents to response format
            response_data = []
            for reservation in reservations:
                reservation_data = {
                    "id": str(reservation["_id"]),
                    "customerName": reservation["customerName"],
                    "customerPhone": reservation["customerPhone"],
                    "customerEmail": reservation["customerEmail"],
                    "date": reservation["date"],
                    "time": reservation["time"],
                    "guests": reservation["guests"],
                    "status": reservation["status"],
                    "special_requests": reservation.get("special_requests"),
                    "created_at": reservation["created_at"],
                    "updated_at": reservation["updated_at"]
                }
                response_data.append(ReservationResponse(**reservation_data))
            return response_data
        else:
            # Development fallback
            filtered_reservations = SAMPLE_RESERVATIONS
            if status:
                filtered_reservations = [reservation for reservation in SAMPLE_RESERVATIONS if reservation["status"] == status]
            return [ReservationResponse(**reservation) for reservation in filtered_reservations]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reservations: {str(e)}"
        )

@router.post("/", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(reservation_data: ReservationCreate):
    """Create a new reservation"""
    try:
        reservations_collection = await get_collection("reservations")

        reservation_doc = {
            "customerName": reservation_data.customerName,
            "customerPhone": reservation_data.customerPhone,
            "customerEmail": reservation_data.customerEmail,
            "date": reservation_data.date,
            "time": reservation_data.time,
            "guests": reservation_data.guests,
            "status": "pending",
            "special_requests": reservation_data.special_requests,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if reservations_collection is not None:
            result = await reservations_collection.insert_one(reservation_doc)
            reservation_id = str(result.inserted_id)
        else:
            # Development fallback
            reservation_id = f"dev_{len(SAMPLE_RESERVATIONS) + 1}"
            reservation_doc["id"] = reservation_id
            SAMPLE_RESERVATIONS.append(reservation_doc)
        
        return ReservationResponse(
            id=reservation_id,
            **reservation_doc
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reservation: {str(e)}"
        )

@router.put("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(reservation_id: str, reservation_update: ReservationUpdate, current_user: dict = Depends(verify_token)):
    """Update a reservation"""
    try:
        reservations_collection = await get_collection("reservations")
        
        if reservations_collection is not None:
            from bson import ObjectId
            
            update_data = {}
            for field, value in reservation_update.dict(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = value
            update_data["updated_at"] = datetime.utcnow()

            result = await reservations_collection.find_one_and_update(
                {"_id": ObjectId(reservation_id)},
                {"$set": update_data},
                return_document=True
            )
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Reservation not found"
                )
            
            # Convert MongoDB document to response format
            reservation_data = {
                "id": str(result["_id"]),
                "customerName": result["customerName"],
                "customerPhone": result["customerPhone"],
                "customerEmail": result["customerEmail"],
                "date": result["date"],
                "time": result["time"],
                "guests": result["guests"],
                "status": result["status"],
                "special_requests": result.get("special_requests"),
                "created_at": result["created_at"],
                "updated_at": result["updated_at"]
            }
            return ReservationResponse(**reservation_data)
        else:
            # Development fallback
            for reservation in SAMPLE_RESERVATIONS:
                if reservation["id"] == reservation_id:
                    for field, value in reservation_update.dict(exclude_unset=True).items():
                        if value is not None:
                            reservation[field] = value
                    reservation["updated_at"] = datetime.utcnow()
                    return ReservationResponse(**reservation)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update reservation: {str(e)}"
        )

@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation(reservation_id: str, current_user: dict = Depends(verify_token)):
    """Delete a reservation"""
    try:
        reservations_collection = await get_collection("reservations")
        
        if reservations_collection is not None:
            from bson import ObjectId
            result = await reservations_collection.delete_one({"_id": ObjectId(reservation_id)})
            if result.deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Reservation not found"
                )
        else:
            # Development fallback
            for i, reservation in enumerate(SAMPLE_RESERVATIONS):
                if reservation["id"] == reservation_id:
                    SAMPLE_RESERVATIONS.pop(i)
                    return
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reservation: {str(e)}"
        )

@router.get("/stats")
async def get_reservation_stats():
    """Get reservation statistics"""
    try:
        reservations_collection = await get_collection("reservations")
        
        if reservations_collection is not None:
            # Sample aggregation
            total_reservations = await reservations_collection.count_documents({})
            confirmed_reservations = await reservations_collection.count_documents({"status": "confirmed"})
            
            return {
                "total_reservations": total_reservations,
                "confirmed_reservations": confirmed_reservations
            }
        else:
            # Development fallback
            total_reservations = len(SAMPLE_RESERVATIONS)
            confirmed_reservations = len([reservation for reservation in SAMPLE_RESERVATIONS if reservation["status"] == "confirmed"])
            
            return {
                "total_reservations": total_reservations,
                "confirmed_reservations": confirmed_reservations
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reservation stats: {str(e)}"
        )

@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(reservation_id: str, current_user: dict = Depends(verify_token)):
    """Get a specific reservation"""
    try:
        reservations_collection = await get_collection("reservations")
        
        if reservations_collection is not None:
            from bson import ObjectId
            reservation = await reservations_collection.find_one({"_id": ObjectId(reservation_id)})
            if not reservation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Reservation not found"
                )
            
            # Convert MongoDB document to response format
            reservation_data = {
                "id": str(reservation["_id"]),
                "customerName": reservation["customerName"],
                "customerPhone": reservation["customerPhone"],
                "customerEmail": reservation["customerEmail"],
                "date": reservation["date"],
                "time": reservation["time"],
                "guests": reservation["guests"],
                "status": reservation["status"],
                "special_requests": reservation.get("special_requests"),
                "created_at": reservation["created_at"],
                "updated_at": reservation["updated_at"]
            }
            return ReservationResponse(**reservation_data)
        else:
            # Development fallback
            for reservation in SAMPLE_RESERVATIONS:
                if reservation["id"] == reservation_id:
                    return ReservationResponse(**reservation)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reservation: {str(e)}"
        )

