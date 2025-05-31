# Use Python 3.10 slim base image
FROM python:3.10.0-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (optional, add if your app needs them)
# RUN apt-get update && apt-get install -y some-package && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files into container
COPY . .

# Expose port 8080 (Fly.io default)
EXPOSE 8080

# Set environment variables for Flask to run on 0.0.0.0:8080
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8080

# If you have a setup_db.py that initializes DB, run it before starting Flask
CMD ["sh", "-c", "python setup_db.py && flask run"]
