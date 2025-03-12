from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from browser_use import Agent
from langchain_openai import ChatOpenAI
from datetime import datetime
import os

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global variable to store the agent instance
agent = None

class BrowseRequest(BaseModel):
    url: str
    task: str

class BrowseResponse(BaseModel):
    result: str

def get_agent():
    global agent
    if agent is None:
        agent = Agent(
            llm=ChatOpenAI(model="gpt-4"),
            options={"headless": True}
        )
    return agent

@app.get("/health")
async def health_check():
    try:
        # Check if agent can be initialized
        agent = get_agent()
        if agent is None:
            return {
                "status": "unhealthy",
                "service": "browser-ai-backend",
                "message": "Agent not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "healthy",
            "service": "browser-ai-backend",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "browser-ai-backend",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/browse", response_model=BrowseResponse)
async def browse(request: BrowseRequest):
    try:
        agent = get_agent()
        result = agent.browse(request.url, request.task)
        return BrowseResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
