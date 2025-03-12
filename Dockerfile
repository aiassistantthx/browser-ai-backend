FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 8000

# Add healthcheck with longer initial delay
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application with longer startup timeout
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]