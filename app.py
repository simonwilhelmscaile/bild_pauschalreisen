"""Main FastAPI application for Social Listening Service.

Run with: uvicorn app:app --reload --port 8000
Or: python app.py
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import setup_logging

setup_logging()

from fastapi import FastAPI
from routes import router
from blog.router import router as blog_router

app = FastAPI(
    title="Beurer Social Listening Service",
    description="Crawls German health forums and review platforms for user discussions about health devices.",
    version="1.0.0"
)

# Include the social listening router
app.include_router(router, prefix="/api/v1")

# Include the blog pipeline router
app.include_router(blog_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Beurer Social Listening Service",
        "docs": "/docs",
        "health": "/api/v1/social-listening/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
