from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.core.database import init_db, close_db
from app.routes import auth, menu, orders, reservations, admin, table_reservations

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

# Initialize FastAPI app
app = FastAPI(
    title="Restaurant Menus API",
    description="""
    🍽️ **Restaurant Management System API**
    
    This is a comprehensive API for managing restaurant operations including:
    
    * **Menu Management** - Add, update, delete menu items
    * **Order Processing** - Handle customer orders and status updates
    * **Reservation System** - Manage table bookings
    * **User Authentication** - Admin and customer authentication
    * **Analytics** - Get insights about restaurant performance
    
    ## Authentication
    
    Most endpoints require authentication. Use the `/auth/login` endpoint to get an access token.
    
    ## Getting Started
    
    1. Create an admin account using `/auth/register`
    2. Login to get your access token
    3. Use the token in the Authorization header: `Bearer <your_token>`
    
    ## Support
    
    For support, contact us at support@restaurant.com
    """,
    version="1.0.0",
    contact={
        "name": "restaurant Support",
        "email": "support@restaurant.com",
        "url": "https://restaurant.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    lifespan=lifespan
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if allowed_origins and allowed_origins[0]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Create directories if they don't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("static/images/menu", exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(menu.router, prefix="/api/menu", tags=["Menu Management"])
app.include_router(orders.router, prefix="/api/orders", tags=["Order Management"])
app.include_router(reservations.router, prefix="/api/reservations", tags=["Reservation Management"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin Panel"])
app.include_router(table_reservations.router, prefix="/api/table-reservations", tags=["Table Reservations"])

@app.get("/", tags=["Root"])
async def root():
    """
    Welcome endpoint - API health check
    """
    return {
        "message": "🍽️ Welcome to restaurant Menu API!",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "restaurant API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
