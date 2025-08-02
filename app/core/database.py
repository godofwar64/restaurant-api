from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def get_database():
    return db.database

async def init_db():
    """Initialize database connection"""
    try:
        # Get MongoDB URI from environment
        mongodb_uri = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        db_name = os.getenv("DATABASE_NAME", "restaurant_db")
        
        # Create MongoDB client
        db.client = AsyncIOMotorClient(mongodb_uri)
        
        # Test connection
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB!")
        
        # Get database
        db.database = db.client[db_name]
        
        # Create indexes if needed
        await create_indexes()
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # For development, we'll continue without database
        logger.warning("Continuing without database connection for development...")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

async def close_db():
    """Close database connection"""
    if db.client:
        db.client.close()
        logger.info("Database connection closed")

async def create_indexes():
    """Create database indexes for better performance"""
    if db.database is None:
        return
        
    try:
        # Users collection indexes
        await db.database.users.create_index("email", unique=True)
        await db.database.users.create_index("username", unique=True)
        
        # Menu items indexes
        await db.database.menu_items.create_index("category")
        await db.database.menu_items.create_index("is_available")
        
        # Orders indexes
        await db.database.orders.create_index("user_id")
        await db.database.orders.create_index("status")
        await db.database.orders.create_index("created_at")
        
        # Reservations indexes
        await db.database.reservations.create_index("user_id")
        await db.database.reservations.create_index("date")
        await db.database.reservations.create_index("status")
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

# Helper function to get collection
async def get_collection(collection_name: str):
    """Get a database collection"""
    if db.database is not None:
        return db.database[collection_name]
    return None
