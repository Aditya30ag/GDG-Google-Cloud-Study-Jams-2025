#!/usr/bin/env python3
"""
FastAPI server to trigger the scraper when refresh is clicked on the site.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import subprocess
import sys
import os
from datetime import datetime
from typing import Dict, Optional

app = FastAPI(
    title="GDG Cloud Study Jams Refresh API",
    description="API to refresh and update study jams progress data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/refresh", response_model=Dict[str, Optional[str]])
async def refresh_data():
    """
    Run the scraper and return results
    
    Returns:
        dict: Contains success status, output and any error messages
    """
    try:
        # Get the path to scrape_profiles.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_path = os.path.join(script_dir, 'scrape_profiles.py')
        data_path = os.path.join(os.path.dirname(script_dir), 'main', 'data.json')
        
        # Run the scraper with default settings
        result = subprocess.run(
            [sys.executable, scraper_path, '--input', data_path, '--output', data_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        return {
            'success': str(result.returncode == 0),
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Scraper timed out after 5 minutes"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == '__main__':
    import uvicorn
    
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Starting refresh server on http://{host}:{port}")
    print("Make sure to keep this running while using the site!")
    print("API Documentation available at: http://localhost:5001/docs")
    
    uvicorn.run(
        "refresh_server:app",
        host=host,
        port=port,
        reload=True if os.environ.get('DEBUG', 'False').lower() == 'true' else False
    )
