# Browser AI Backend

This is the backend service for the Browser AI Chrome extension, which provides AI-powered browser automation capabilities using the browser-use library and OpenAI's language models.

## Features

- FastAPI server with WebSocket support for real-time updates
- Integration with browser-use for browser automation
- OpenAI language model integration
- CORS support for Chrome extension
- Robust error handling and logging
- Docker support for easy deployment

## Prerequisites

- Python 3.11 or higher
- Chrome browser installed
- OpenAI API key

## Setup

1. Clone the repository:
```bash
git clone https://github.com/aiassistantthx/browser-ai-backend.git
cd browser-ai-backend
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Running the Server

### Local Development

```bash
python main.py
```

The server will start on `http://localhost:8000`.

### Using Docker

1. Build the Docker image:
```bash
docker build -t browser-ai-backend .
```

2. Run the container:
```bash
docker run -p 8000:8000 -e OPENAI_API_KEY=your_api_key_here browser-ai-backend
```

## API Endpoints

- `POST /tasks`: Create a new browser automation task
- `GET /tasks/{task_id}`: Get the status and result of a task
- `WebSocket /ws`: Real-time updates for task status and results

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

## Deployment

The service can be deployed to any platform that supports Docker containers. We recommend using platforms like:

- Render.com
- DigitalOcean
- Heroku
- AWS Elastic Beanstalk

Make sure to set the `OPENAI_API_KEY` environment variable in your deployment environment.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.