#!/bin/bash

# HydroClaude Web API Server Startup Script
# Usage: ./start_server.sh [--port PORT] [--reload]

set -e

# Default configuration
PORT=8000
RELOAD=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --reload)
            RELOAD="--reload"
            shift
            ;;
        --help)
            echo "HydroClaude Web API Server"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT    Port to run server on (default: 8000)"
            echo "  --reload       Enable auto-reload on code changes"
            echo "  --help         Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set environment variables
export HYDROCLAUDE_PATH="${HYDROCLAUDE_PATH:-/home/user/HydroClaude}"

# Print startup banner
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           HydroClaude Web API Server                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Port: $PORT"
echo "  HydroClaude Path: $HYDROCLAUDE_PATH"
echo "  Auto-reload: ${RELOAD:-disabled}"
echo ""
echo "API Documentation:"
echo "  Swagger UI: http://localhost:$PORT/api/docs"
echo "  ReDoc:      http://localhost:$PORT/api/redoc"
echo "  Health:     http://localhost:$PORT/health"
echo ""
echo "Starting server..."
echo "═══════════════════════════════════════════════════════════"
echo ""

# Change to API gateway directory
cd "$(dirname "$0")/api_gateway"

# Start uvicorn server
uvicorn main:app --host 0.0.0.0 --port "$PORT" $RELOAD
