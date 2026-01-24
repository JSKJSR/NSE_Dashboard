#!/bin/bash
# Stop the NSE Bias Dashboard Streamlit server.

PROJECT_DIR="/Users/shobha/Documents/Python_Learn/NSE_Dashboard"
PID_FILE="$PROJECT_DIR/logs/streamlit.pid"
PORT=8501

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping Streamlit (PID: $PID)..."
        kill "$PID"
        rm -f "$PID_FILE"
        echo "Stopped."
    else
        echo "PID $PID not running. Cleaning up."
        rm -f "$PID_FILE"
    fi
else
    # Fallback: kill by port
    PIDS=$(lsof -ti :$PORT 2>/dev/null)
    if [ -n "$PIDS" ]; then
        echo "Stopping processes on port $PORT: $PIDS"
        echo "$PIDS" | xargs kill
        echo "Stopped."
    else
        echo "No dashboard process found."
    fi
fi
