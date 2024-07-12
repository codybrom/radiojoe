# Radiojoe - Internet Radio Recorder

This project is a Python script that records internet radio shows and downloads them for later listening. The recording schedule and stream URLs are managed via a configuration file, and the script uses environment variables for flexible deployment.

## Prerequisites

- Python 3
- ffmpeg
- Virtual environment (recommended)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/codybrom/radiojoe.git
   cd internet-radio-recorder
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required Python libraries:
   ```bash
   pip install schedule pytz 
   ```

## Configuration

1. Create a `config.json` file in the root directory with your show details:

   ```json
   {
     "shows": [
       {
         "name": "WESS",
         "url": "http://wessstream.esu.edu:8000/play",
         "day": "Monday",
         "time": "10:00 PM",
         "timezone": "America/New_York",
         "duration": 3600
       },
       // Add other shows here
     ]
   }
   ```

2. Create a `run_recorder.sh` script to set environment variables and run the Python script:

   ```bash
   #!/bin/bash

   # Set environment variables
   export RADIOJOE_BASE_DIR="/path/to/your/project"
   export RADIOJOE_LOG_FILE="$RADIOJOE_BASE_DIR/recorder.log"
   export RADIOJOE_OUTPUT_DIR="$RADIOJOE_BASE_DIR/recordings"
   export RADIOJOE_CONFIG_FILE="$RADIOJOE_BASE_DIR/config.json"

   # Set the working directory
   cd "$RADIOJOE_BASE_DIR"

   # Activate virtual environment
   source /path/to/your/project/venv/bin/activate

   # Run the Python script
   python3 "$RADIOJOE_BASE_DIR/recorder.py"
   ```

   Make sure to update the paths in this script to match your system.

## Running the Script

Make the run script executable and run it:

```bash
chmod +x run_recorder.sh
./run_recorder.sh
```

## Automating with Crontab

To ensure the script runs at system startup:

1. Open the crontab editor:
   ```bash
   crontab -e
   ```

2. Add the following entry:
   ```
   @reboot /path/to/your/project/run_recorder.sh >> /path/to/your/project/recorder.log 2>&1
   ```

   Replace `/path/to/your/project` with the actual path to your project directory.

## Project Structure

- `recorder.py`: The main Python script that handles scheduling and recording.
- `config.json`: Configuration file for show details.
- `run_recorder.sh`: Bash script to set environment variables and run the Python script.
- `recordings/`: Directory where recorded shows are saved (created automatically).
- `recorder.log`: Log file for the script's operations.

## Customization

You can customize the following environment variables in `run_recorder.sh`:

- `RADIOJOE_BASE_DIR`: The base directory of the project.
- `RADIOJOE_LOG_FILE`: Path to the log file.
- `RADIOJOE_OUTPUT_DIR`: Directory where recordings are saved.
- `RADIOJOE_CONFIG_FILE`: Path to the configuration file.

## Troubleshooting

- If the script isn't running as expected, check the `recorder.log` file for error messages.
- Ensure that ffmpeg is installed and accessible in your system's PATH.
- Verify that the URLs in your `config.json` are correct and accessible.

## Contributing

Feel free to fork this project and submit pull requests with any improvements or bug fixes.