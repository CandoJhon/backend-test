from fastapi import FastAPI

app = FastAPI()

@app.get("/app")
def read_root():
    return {"message": "Hello from IBM Cloud Code Engine"}
