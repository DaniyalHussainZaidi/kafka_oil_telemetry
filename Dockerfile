# Use an official lightweight Python image
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies needed for confluent-kafka 
RUN apt-get update && apt-get install -y \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# copy requirements from the scripts folder
COPY scripts/requirements.txt .

# install python dependencies 
RUN pip install --no-cache-dir -r requirements.txt

# copy scripts in container
COPY scripts/ .

