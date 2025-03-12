# Browser AI Backend

Backend service for browser automation using browser-use and FastAPI.

## Features

- Browser automation with browser-use
- Real-time task status updates via WebSocket
- FastAPI REST endpoints
- Docker support

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and add your OpenAI API key
3. Install dependencies:
```bash
pip install -r requirements.txt
playwright install
```

4. Run the server:
```bash
python main.py
```

## Docker

To run with Docker:

```bash
docker build -t browser-ai-backend .
docker run -p 8000:8000 browser-ai-backend
```

## API Endpoints

- POST `/tasks` - Create a new browser automation task
- GET `/tasks/{task_id}` - Get task status and result
- WebSocket `/ws` - Real-time task updates

## Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key