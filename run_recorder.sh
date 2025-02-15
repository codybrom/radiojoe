#!/bin/bash
set -o pipefail

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Set the default configuration file path relative to the script directory
CONFIG_FILE="${RADIOJOE_CONFIG_FILE:-$SCRIPT_DIR/config.json}"

echo "Script directory: $SCRIPT_DIR"
echo "Looking for config file at: $CONFIG_FILE"

# Check if the config file exists.
if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: Configuration file not found: $CONFIG_FILE"
  echo "Files in script directory:"
  ls -la "$SCRIPT_DIR"
  exit 1
fi

echo "Using configuration file: $CONFIG_FILE"

# Helper function to extract a value from the config string.
# This function assumes simple key-value pairs and is not robust to complex JSON structures.
get_config_value() {
  local key="$1"
  # Extract value based on the key, using basic string manipulation.
  local VALUE=$(grep "\"${key}\"\:" "$CONFIG_FILE" | sed -E 's/.*: *"?([^"]*)"?,?.*/\1/')
  if [ -n "$VALUE" ]; then
    echo "$VALUE"
  else
    echo "WARNING: Key '$key' not found in $CONFIG_FILE"
    echo ""  # Return an empty string if the key is not found
  fi
}

# Load values from config file
BASE_DIR="$(get_config_value "base_dir")"
DEBUG_LOG="$(get_config_value "log_file")"
OUTPUT_DIR="$(get_config_value "output_dir")"
STATUS_FILE="$(get_config_value "status_file")"

# Ensure BASE_DIR is set
if [ -z "$BASE_DIR" ]; then
  echo "ERROR: base_dir not set in config file"
  exit 1
fi

# Change to the base directory
cd "$BASE_DIR" || exit 1

# Create the debug log if it doesn't exist
if [ ! -f "$DEBUG_LOG" ]; then
  touch "$DEBUG_LOG"
fi

# Add a function to log messages, as this keeps the main script cleaner
log() {
  echo "$(date) - $1" >> "$DEBUG_LOG"
}

log "Script started"
log "Current working directory: $(pwd)"

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
  if [ -d "$BASE_DIR/.venv/bin" ]; then
      log "Activating virtual environment"
      source "$BASE_DIR/.venv/bin/activate"
      log "Virtual environment activated: $VIRTUAL_ENV"
  else
      log "ERROR: Virtual environment directory not found: $BASE_DIR/.venv/bin. Is the virtual environment set up?"
      exit 1
  fi
else
  log "Virtual environment already active: $VIRTUAL_ENV"
fi

#Export Flask variables
export FLASK_APP="app.py"
export FLASK_RUN_PORT=5000  # Change this if you want a different port
export FLASK_DEBUG=0  # Set to "1" for debug mode (development only!)

# Run the Python scripts
log "Starting recorder.py"
python3 recorder.py >> "$DEBUG_LOG" 2>&1 &  # Run in background
RECORDER_PID=$! #Capture process id

log "Starting app.py (Flask web app)"
flask run  >> "$DEBUG_LOG" 2>&1 # Run in the foreground. Prevents it from closing immediately.
exit_code=$?

log "App.py finished with exit code $exit_code"
log "Killing recorder.py"
kill $RECORDER_PID #Terminate radio app on exit
exit $exit_code # Exit from the main thread.