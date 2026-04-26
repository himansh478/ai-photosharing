#!/bin/bash
echo "--- AI Photo Sharing Startup Sequence ---"
echo "Current Directory: $(pwd)"
echo "Installing critical system libraries..."
apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0

echo "Checking Python environment..."
pip install --upgrade pip

echo "Starting Gunicorn from backend folder..."
cd backend
gunicorn --bind=0.0.0.0:7860 --timeout 600 --workers 1 app:app
