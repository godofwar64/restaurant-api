from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from jose import jwt
import bcrypt
import os
from datetime import datetime, timedelta
from app.core.database import get_collection
from bson import ObjectId

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "customer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str

class User(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    created_at: datetime

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """Register a new user"""
    try:
        users_collection = await get_collection("users")
        
        # Check if user already exists
        if users_collection is not None:
            existing_user = await users_collection.find_one({"email": user_data.email})
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            existing_username = await users_collection.find_one({"username": user_data.username})
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user document
        user_doc = {
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password,
            "full_name": user_data.full_name,
            "role": user_data.role,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        # Insert user into database
        if users_collection is not None:
            result = await users_collection.insert_one(user_doc)
            user_id = str(result.inserted_id)
        else:
            # Fallback for development without database
            user_id = "dev_user_id"
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id, "role": user_data.role},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "role": user_data.role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Login user"""
    try:
        print(f"🔐 Login attempt for email: {user_credentials.email}")
        
        # Get users collection
        users_collection = await get_collection("users")
        
        if users_collection is not None:
            # Find user in database
            user = await users_collection.find_one({"email": user_credentials.email})
            
            if not user:
                print(f"❌ User not found for email: {user_credentials.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if user is active
            if not user.get("is_active", True):
                print(f"❌ User account is inactive for email: {user_credentials.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Verify password
            stored_password = user.get("password")
            if not stored_password or not verify_password(user_credentials.password, stored_password):
                print(f"❌ Invalid password for email: {user_credentials.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_id = str(user["_id"])
            role = user.get("role", "customer")
            
            print(f"✅ Login successful for user: {user_credentials.email} (Role: {role})")
            
        else:
            # Fallback to hardcoded credentials for development without database
            print("⚠️ Database not available, using hardcoded credentials")
            admin_email = "admin@restauranrfresh.com"
            admin_password = "admin123"
            
            if user_credentials.email == admin_email and user_credentials.password == admin_password:
                user_id = "dev_admin_id"
                role = "admin"
                print(f"✅ Fallback admin login successful!")
            else:
                print(f"❌ Invalid credentials")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id, "role": role},
            expires_delta=access_token_expires
        )
        
        print(f"🎟️ Token created successfully")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "role": role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/me", response_model=User)
async def get_current_user(current_user: dict = Depends(verify_token)):
    """Get current user information"""
    try:
        users_collection = await get_collection("users")
        
        if users_collection is not None:
            try:
                # Convert user_id to ObjectId if it's a valid ObjectId string
                user_id = current_user["sub"]
                if ObjectId.is_valid(user_id):
                    query = {"_id": ObjectId(user_id)}
                else:
                    # Fallback for non-ObjectId user_ids (like dev_admin_id)
                    query = {"_id": user_id}
                
                user = await users_collection.find_one(query)
                
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                
                return User(
                    id=str(user["_id"]),
                    username=user["username"],
                    email=user["email"],
                    full_name=user.get("full_name"),
                    role=user["role"],
                    created_at=user["created_at"]
                )
            except Exception as db_error:
                print(f"Database error in get_current_user: {db_error}")
                # Fall through to development fallback
        
        # Fallback for development or database errors
        return User(
            id=current_user["sub"],
            username="dev_user",
            email="dev@restauranrfresh.com",
            full_name="Development User",
            role=current_user["role"],
            created_at=datetime.utcnow()
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )
