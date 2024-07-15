# Radiojoe - Internet Radio Recorder

This project is a Python script that records internet radio shows and downloads them for later listening. The recording schedule and stream URLs are managed via a configuration file, and the script uses environment variables for flexible deployment.

## Prerequisites

- Python 3
- ffmpeg
- Virtual environment (recommended)

## Features
- Schedule recordings for specific days and times.
- Record multiple shows concurrently.
- Automatic file naming and organization.
- Configuration file for easy management of show details.
- Environment variables for flexible deployment.
- Test the schedule to verify stream availability.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/codybrom/radiojoe.git
   cd radiojoe
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required Python libraries:
   ```bash
   pip install schedule pytz requests
   ```

## Configuration

1. Create a `config.json` file in the root directory with your show details. Duration is measured in seconds (3600 = 1 hour)

   ```json
   {
     "shows": [
       {
         "name": "KEXP",
         "url": "https://stream.kexp.org/kexp1",
         "day": "Sunday",
         "time": "10:00 AM",
         "timezone": "America/Los_Angeles",
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

## Testing the Schedule

The `show_schedule.py` script allows you to test the upcoming schedule and verify the availability of the streams. To run the schedule test:

1. Make sure you're in the project directory and your virtual environment is activated.
2. Run the following command:

   ```bash
   python3 show_schedule.py
   ```

This will display the upcoming recordings for the next 7 days, organized by date. For each show, it will test the stream URL and display the status:

- ✅: The stream is accessible and appears to be an audio stream.
- ❓: The stream is accessible but may not be an audio stream.
- ❌: The stream is not accessible or there was an error.
- ⏳: The connection timed out.

This test helps ensure that your configured streams are working correctly before the scheduled recording time.

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
- `show_schedule.py`: Script to test and display the upcoming schedule.
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
- Use the `show_schedule.py` script to test the availability of your configured streams.

## Contributing

Feel free to fork this project and submit pull requests with any improvements or bug fixes.