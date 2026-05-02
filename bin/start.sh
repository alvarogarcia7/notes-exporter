#!/bin/bash
# Start Apple Notes publisher via notes-exporter
set -e

PARSER_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$PARSER_ROOT/.." && pwd)"

# Load environment from parent .env if it exists
if [ -f "$REPO_ROOT/.env" ]; then
    export $(grep -v '^#' "$REPO_ROOT/.env" | xargs)
fi

# Set defaults if not already set
export NATS_URL="${NATS_URL:-tls://docker:4222}"
export CERTS_DIR="${CERTS_DIR:-$REPO_ROOT/nats/certs}"

# Activate virtual environment if it exists
if [ -f "$PARSER_ROOT/.venv/bin/activate" ]; then
    source "$PARSER_ROOT/.venv/bin/activate"
fi

# Change to parser directory
cd "$PARSER_ROOT"

# Determine data directory
DATA_DIR="${NOTES_EXPORT_DATA_DIR:-./data}"

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "⚠ Data directory '$DATA_DIR' not found"
    echo "Please export Apple Notes using notes-exporter first:"
    echo "  ./exportnotes.zsh"
    echo "Then run this script again"
    exit 1
fi

# Start publisher
python3 nats_publisher.py --data-dir "$DATA_DIR"
