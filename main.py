from fastapi import FastAPI
import uvicorn
import os

# Create FastAPI instance
app = FastAPI(title="Backend Test API", version="1.0.0")

# Health check endpoint
@app.get("/")
def read_root():
    return {"message": "Hello World", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Example endpoint
@app.get("/api/test")
def test_endpoint():
    return {"message": "Test endpoint working!"}

# This is important for IBM Cloud Code Engine
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # IBM Cloud Code Engine uses PORT env var
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")