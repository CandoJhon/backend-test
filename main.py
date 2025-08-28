
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import uvicorn
import os
import logging
from auth.app_id_auth import AppIDAuth

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI instance
app = FastAPI(title="Backend Test API", version="1.0.1")

# Database connection (optional for now)
try:
    # Your database connection code would go here
    # For now, we'll just log that we're skipping it
    logger.info("Database connection skipped for testing")
    DB_CONNECTED = False
except Exception as e:
    logger.warning(f"Database connection failed: {e}")
    DB_CONNECTED = False

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize IBM App ID
app_id_auth = AppIDAuth(
    region=os.getenv("APPID_REGION", "us-south"),
    tenant_id=os.getenv("APPID_TENANT_ID"),
    client_id=os.getenv("APPID_CLIENT_ID"),
    secret=os.getenv("APPID_SECRET")
)

# Security scheme
security = HTTPBearer()

# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate IBM App ID token and get user info"""
    try:
        user_info = await app_id_auth.verify_token(credentials.credentials)
        return user_info
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/")
def read_root():
    return {
        "message": "Backend API with IBM App ID And Database Without Connection", 
        "status": "healthy",
        "auth_provider": "IBM App ID"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "auth": "IBM App ID", "Database": "Without Connection"}

@app.get("/auth/login-url")
async def get_login_url():
    """Get IBM App ID login URL"""
    try:
        login_url = app_id_auth.get_login_url()
        return {"login_url": login_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/callback")
async def auth_callback(code: str, state: str = None):
    """Handle OAuth callback from IBM App ID"""
    try:
        redirect_uri = os.getenv("APPID_REDIRECT_URI", "https://back-appid-01.1z0cxvgkml9e.us-east.codeengine.appdomain.cloud/auth/callback")
        tokens = await app_id_auth.exchange_code_for_tokens(code, redirect_uri=redirect_uri)
        user_info = await app_id_auth.get_user_info(tokens["access_token"])
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "user_info": user_info,
            "expires_in": tokens.get("expires_in")
        }
    except Exception as e:
        logger.error(f"Authentication callback failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    

#debug auth/callback
@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Debug the callback to see raw parameters"""
    
    # Log everything we receive
    logger.info(f"Query params: {dict(request.query_params)}")
    logger.info(f"Raw query string: {request.url.query}")
    
    code = request.query_params.get('code')
    logger.info(f"Extracted code: {code}")
    logger.info(f"Code length: {len(code) if code else 0}")
    
    return {
        "received_code": code,
        "code_length": len(code) if code else 0,
        "raw_query": str(request.url.query),
        "all_params": dict(request.query_params)
    }

@app.get("/auth/user", dependencies=[Depends(get_current_user)])
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile (protected route)"""
    return {
        "user": current_user,
        "message": "Successfully authenticated with IBM App ID"
    }

@app.get("/api/protected", dependencies=[Depends(get_current_user)])
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    """Protected API endpoint"""
    return {
        "message": "This is a protected endpoint",
        "user_id": current_user.get("sub"),
        "user_email": current_user.get("email"),
        "data": [
            {"id": 1, "title": "Protected Item 1"},
            {"id": 2, "title": "Protected Item 2"},
            {"id": 3, "title": "Protected Item 3"}
        ]
    }

@app.get("/debug/token")
async def debug_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Debug token validation"""
    try:
        token = credentials.credentials
        logger.info(f"Received token (first 50 chars): {token[:50]}...")
        
        # Try to get user info directly
        user_info = await app_id_auth.get_user_info(token)
        return {
            "message": "Token is valid",
            "user_info": user_info
        }
    except Exception as e:
        logger.error(f"Token debug failed: {e}")
        return {
            "error": str(e),
            "message": "Token validation failed"
        }

@app.get("/api/public")
async def public_endpoint():
    """Public API endpoint"""
    return {
        "message": "This is a public endpoint",
        "data": [
            {"id": 1, "title": "Public Item 1"},
            {"id": 2, "title": "Public Item 2"}
        ]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting FastAPI server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")