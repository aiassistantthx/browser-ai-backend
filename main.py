import os
import json
import logging
import asyncio
import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Get port from environment variable with fallback to 8000
PORT = int(os.getenv("PORT", "8000"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "http://localhost:*", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
agent = None
browser = None

def get_agent():
    global agent, browser
    if agent is None:
        browser_config = BrowserConfig(headless=True, disable_security=True)
        browser = Browser(config=browser_config)
        agent = Agent(
            task="I am a browser automation agent. I will help you with web tasks.",
            llm=ChatOpenAI(model="gpt-4"),
            browser=browser
        )
    return agent

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        # Basic service health check - don't check agent here
        return {
            "status": "healthy",
            "service": "browser-ai-backend",
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

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
        
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()
tasks: Dict[str, TaskResponse] = {}

@app.post("/tasks")
async def create_task(request: TaskRequest):
    try:
        logger.info(f"Received task request: {request}")
        task_id = str(len(tasks) + 1)
        task = TaskResponse(id=task_id, status="pending")
        tasks[task_id] = task
        
        asyncio.create_task(execute_task(task_id, request))
        return task
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_task(task_id: str, request: TaskRequest):
    task = tasks[task_id]
    try:
        task.status = "processing"
        await manager.broadcast({"type": "status", "task_id": task_id, "status": "processing"})
        logger.info(f"Processing task {task_id}: {request.task}")
        
        # Get agent instance and execute browser automation
        current_agent = get_agent()
        result = await current_agent.run(
            task=request.task,
            initial_url=request.context.url,
            context={"page_title": request.context.title}
        )
        
        logger.info(f"Task {task_id} completed with result: {result}")
        
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
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )