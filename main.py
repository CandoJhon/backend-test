
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from urllib.parse import unquote
import base64
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
from urllib.parse import unquote
import base64

@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback with proper encoding"""
    try:
        # Get raw code parameter
        raw_code = request.query_params.get('code')
        logger.info(f"Raw code received (length: {len(raw_code)}): {raw_code[:100]}...")
        
        # Try to decode if it's URL encoded
        try:
            decoded_code = unquote(raw_code)
            logger.info(f"URL decoded code (length: {len(decoded_code)}): {decoded_code[:100]}...")
            
            # If still looks corrupted, might be base64 or other encoding
            if len(decoded_code) > 200:  # Still too long
                logger.warning("Code still appears corrupted after URL decoding")
                # Try different decoding approaches
                
        except Exception as decode_error:
            logger.error(f"Decoding failed: {decode_error}")
            decoded_code = raw_code
        
        # Use the best version of the code
        final_code = decoded_code if len(decoded_code) < len(raw_code) else raw_code
        
        logger.info(f"Using final code (length: {len(final_code)}): {final_code[:50]}...")
        
        # Try token exchange with cleaned code
        redirect_uri = os.getenv("APPID_REDIRECT_URI")
        tokens = await app_id_auth.exchange_code_for_tokens(final_code, redirect_uri=redirect_uri)
        user_info = await app_id_auth.get_user_info(tokens["access_token"])
        
        return {
            "status": "success",
            "access_token": tokens["access_token"],
            "user_info": user_info
        }
        
    except Exception as e:
        logger.error(f"Callback failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "received_code_length": len(raw_code) if 'raw_code' in locals() else 0
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
    
#Debug frontend token
@app.get("/debug/frontend-token")
async def debug_frontend_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Debug what token the frontend is sending"""
    try:
        token = credentials.credentials
        logger.info(f"Frontend token (first 50 chars): {token[:50]}...")
        logger.info(f"Token length: {len(token)}")
        
        # Try to validate it
        user_info = await app_id_auth.verify_token(token)
        return {
            "status": "valid",
            "token_length": len(token),
            "user_info": user_info
        }
    except Exception as e:
        return {
            "status": "invalid",
            "error": str(e),
            "token_length": len(token) if 'token' in locals() else 0
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