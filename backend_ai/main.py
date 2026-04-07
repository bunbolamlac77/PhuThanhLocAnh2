from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from core.engine import ai_engine
from core.database import db

app = FastAPI(title="LocAnh2 AI Backend", version="1.0.0")

# Setup CORS for Tauri frontend (default port 1420)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "status": "online",
        "device": str(ai_engine.device),
        "engine": "LocAnh2 AI Core"
    }

@app.get("/health")
async def health():
    # TODO: Check if AI models are loaded and MPS is available
    return {"status": "healthy", "engine": "ready"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
