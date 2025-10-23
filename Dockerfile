FROM python:3.13.4-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY conversion/requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 10000
EXPOSE 10000

# Command to run the application with uvicorn
CMD ["uvicorn", "conversion.refresh_server:app", "--host", "0.0.0.0", "--port", "10000"]