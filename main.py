import logging
import os
import sys
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import asyncio

# Configure logging to show everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

# Log system information at startup
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Environment variables: {dict(os.environ)}")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store browser instance
browser = None

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup...")
    # Log all mounted routes
    for route in app.routes:
        logger.info(f"Route mounted: {route.path} [{','.join(route.methods)}]")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown...")
    global browser
    if browser:
        await browser.close()
        logger.info("Browser closed")

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Initialize browser on first connection
        global browser
        if not browser:
            logger.info("Initializing browser...")
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox']
            )
            logger.info("Browser initialized successfully")

        # Test browser by creating a page
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        await page.close()
        
        await websocket.send_json({
            "status": "success",
            "message": f"Browser test successful. Page title: {title}"
        })
        
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}", exc_info=True)
        await websocket.send_json({
            "status": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
        logger.info("WebSocket connection closed")