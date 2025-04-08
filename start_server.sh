#!/bin/bash

# Kill any existing Flask processes
echo "Stopping any existing Flask servers..."
pkill -9 -f flask || true

# Find a free port
echo "Checking for available ports..."
python check_ports.py
echo

# Start the server with a specific port
PORT=8080
echo "Starting Flask server on port $PORT..."
python app.py $PORT 