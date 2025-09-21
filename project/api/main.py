from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://deepmu.tech", "https://www.deepmu.tech"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Middleware
@app.on_event("startup")
async def startup():
    # Add security hardening measures here
    pass

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "DeepMu API is running"}