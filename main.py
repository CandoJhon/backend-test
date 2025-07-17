from fastapi import FastAPI
import uvicorn
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI instance
app = FastAPI(title="Backend Test API", version="1.0.0")

# Database connection (optional for now)
try:
    # Your database connection code would go here
    # For now, we'll just log that we're skipping it
    logger.info("Database connection skipped for testing")
    DB_CONNECTED = False
except Exception as e:
    logger.warning(f"Database connection failed: {e}")
    DB_CONNECTED = False

# Health check endpoint
@app.get("/")
def read_root():
    return {
        "message": "Hello World", 
        "status": "healthy",
        "database_connected": DB_CONNECTED
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database_connected": DB_CONNECTED
    }

# Example endpoint
@app.get("/api/test")
def test_endpoint():
    return {"message": "Test endpoint working!", "database_connected": DB_CONNECTED}

# Database status endpoint
@app.get("/api/db-status")
def database_status():
    return {
        "database_connected": DB_CONNECTED,
        "message": "Database connection is optional for this test deployment"
    }

# IMPORTANT: Remove the if __name__ == "__main__" block
# Code Engine will run this with uvicorn command directly