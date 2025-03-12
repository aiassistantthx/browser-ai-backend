import os
import json
import logging
import asyncio
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from browser_use import Browser
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log environment variables (excluding sensitive ones)
logger.info("Environment variables:")
for key, value in os.environ.items():
    if key != "OPENAI_API_KEY":
        logger.info(f"{key}={value}")

# Initialize FastAPI app
app = FastAPI()

# Configure CORS - allow both Chrome extension and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in production (you might want to restrict this)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Browser as None first
browser = None

async def initialize_browser():
    global browser
    try:
        if browser is None:
            logger.info("Initializing Browser...")
            browser = Browser()
            browser.llm = ChatOpenAI(model="o3-mini")
            logger.info("Browser initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Browser: {e}")
        raise

# Data models
class Context(BaseModel):
    url: str
    title: str

class TaskRequest(BaseModel):
    task: str
    context: Context

class TaskResponse(BaseModel):
    id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info("New WebSocket connection established")
            # Send initial status
            await websocket.send_json({"type": "status", "status": "connected"})
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            raise

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
            logger.info("WebSocket connection closed")
        except ValueError:
            logger.warning("Attempted to remove non-existent WebSocket connection")

    async def broadcast(self, message: dict):
        logger.info(f"Broadcasting message: {message}")
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Store tasks
tasks: Dict[str, TaskResponse] = {}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI application...")
    try:
        # Log system information
        import sys
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Directory contents: {os.listdir()}")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}

@app.post("/tasks")
async def create_task(request: TaskRequest):
    try:
        logger.info(f"Received task request: {request}")
        # Initialize browser if not already initialized
        await initialize_browser()
        
        task_id = str(len(tasks) + 1)
        task = TaskResponse(id=task_id, status="pending")
        tasks[task_id] = task
        
        # Execute task in background
        asyncio.create_task(execute_task(task_id, request))
        
        return task
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_task(task_id: str, request: TaskRequest):
    task = tasks[task_id]
    try:
        # Update status
        task.status = "processing"
        await manager.broadcast({"type": "status", "task_id": task_id, "status": "processing"})
        logger.info(f"Processing task {task_id}: {request.task}")
        
        # Execute browser automation
        result = await browser.run(
            task=request.task,
            url=request.context.url
        )
        logger.info(f"Task {task_id} completed with result: {result}")
        
        # Update task with result
        task.status = "completed"
        task.result = result
        await manager.broadcast({
            "type": "result",
            "task_id": task_id,
            "status": "completed",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Error executing task {task_id}: {e}")
        task.status = "failed"
        task.error = str(e)
        await manager.broadcast({
            "type": "error",
            "task_id": task_id,
            "status": "failed",
            "error": str(e)
        })

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    try:
        logger.info(f"Getting task {task_id}")
        task = tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"Received WebSocket message: {data}")
                await websocket.send_json({"status": "received", "type": "ack"})
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )