#!/usr/bin/env python3
"""
FastAPI server to trigger the scraper when refresh is clicked on the site.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
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
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]  # Expose all headers
)

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
main_dir = os.path.join(project_root, 'main')

# Use a writable directory on Render
if os.environ.get('RENDER'):
    data_path = '/tmp/data.json'
    # Copy initial data.json to /tmp if it doesn't exist
    if not os.path.exists(data_path):
        import shutil
        source_data = os.path.join(main_dir, 'data.json')
        if os.path.exists(source_data):
            shutil.copy2(source_data, data_path)
else:
    data_path = os.path.join(main_dir, 'data.json')

# Mount the static files directories
app.mount("/assets", StaticFiles(directory=os.path.join(main_dir, "assets")), name="assets")
app.mount("/static", StaticFiles(directory=main_dir), name="static")

@app.get("/data")
async def get_data():
    """
    Serve the data.json file
    """
    if os.path.exists(data_path):
        return FileResponse(data_path)
    raise HTTPException(status_code=404, detail="Data file not found")

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

@app.get("/")
async def root():
    """Serve the index.html file"""
    index_path = os.path.join(main_dir, 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            content = f.read()
        return HTMLResponse(content=content)
    raise HTTPException(status_code=404, detail="index.html not found")

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
