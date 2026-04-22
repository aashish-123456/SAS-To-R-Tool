#!/bin/bash

echo "========================================"
echo "SAS to R Automation Platform"
echo "Quick Start Script for Mac/Linux"
echo "========================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed!"
    echo "Please install from: https://nodejs.org"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python is not installed!"
    echo "Please install from: https://python.org"
    exit 1
fi

echo "Node.js and Python are installed."
echo ""

echo "========================================"
echo "Starting Frontend Server..."
echo "========================================"

# Start frontend in background
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Waiting 5 seconds before starting backend..."
sleep 5

echo "========================================"
echo "Starting Backend Server..."
echo "========================================"

# Start backend in background
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py &
BACKEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "Both servers are running!"
echo "========================================"
echo ""
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo ""
echo "Opening application in browser..."
sleep 3

# Open browser (works on Mac and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:5173
else
    xdg-open http://localhost:5173 2>/dev/null || echo "Please open http://localhost:5173 in your browser"
fi

echo ""
echo "Press Ctrl+C to stop all servers..."

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping servers...'; kill $FRONTEND_PID $BACKEND_PID 2>/dev/null; echo 'Servers stopped.'; exit" INT

# Keep script running
wait
