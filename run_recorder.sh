#!/bin/bash
set -o pipefail

# Default configuration file.
CONFIG_FILE="${RADIOJOE_CONFIG_FILE:-config.json}"

# Check if the config file exists.
if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: Configuration file not found: $CONFIG_FILE"
  exit 1
fi

# Read the entire config file into a single string.
CONFIG_STRING=$(cat "$CONFIG_FILE")

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

# Create the debug log if it doesn't exist
if [ ! -f "$DEBUG_LOG" ]; then
  touch "$DEBUG_LOG"
fi

# Add a function to log messages, as this keeps the main script cleaner
log() {
  echo "$(date) - $1" >> "$DEBUG_LOG"
}

log "Script started"

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
  if [ -n "$BASE_DIR" ]; then
      if [ -d "$BASE_DIR/venv/bin" ]; then
          log "Activating virtual environment"
          source "$BASE_DIR/venv/bin/activate"
      else
          log "ERROR: Virtual environment directory not found: $BASE_DIR/venv/bin. Is radiojoe corect, and a VENV setup?"
      fi

  else
    log "WARNING: BASE_DIR not set, cannot activate virtual environment."
  fi
else
  log "Virtual environment already active"
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
flask run  >> "$DEBUG_LOG" 2>&1 # Run in the foreground. Prevents it from closing immedeatly.
exit_code=$?

log "App.py finished with exit code $exit_code"
log "Killing recorder.py"
kill $RECORDER_PID #Terminate radio app on exit
exit $exit_code # Exit from the main thread.