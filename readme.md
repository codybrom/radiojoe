# Radiojoe - Internet Radio Recorder

This project is a Python application designed to record internet radio shows automatically. It features a web interface for managing recording schedules, browsing recordings, and editing metadata. The application uses a configuration file for scheduling details and leverages environment variables for flexible deployment.

## Prerequisites

- **Python 3.12**
- ffmpeg (installed and accessible in your system's PATH)
- Virtual environment (recommended)

## Features

- **Scheduling & Recording:**
  - Schedule recordings for specific days and times, recurring weekly.
  - Supports different timezones
  - Concurrent recording of multiple shows.
  - Automatic MP3 tagging

- **Web Interface:**
  - Add, edit, and delete scheduled recordings through a user-friendly web interface.
  - Browse and listen to recorded shows directly from the web interface.
  - Edit MP3 metadata tags (title, artist, album, genre, year, comment).
  - Delete unwanted recordings.
  - View system status (disk usage, CPU usage, memory usage, last recording, next recording).
  - Export recording data in JSON format.

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

3. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Create a `config.json` file in the root directory with your show details. An example configuration (`config.example.json`) is provided. Duration is measured in seconds (3600 = 1 hour)

## Running the Application

1. Make `run_recorder.sh` executable:

    ```bash
    chmod +x run_recorder.sh
    ```

2. Run `run_recorder.sh`. This script starts both the recording process and the Flask web interface.

    ```bash
    ./run_recorder.sh
    ```

3. Open your web browser and navigate to `http://127.0.0.1:5000/` (or the port specified by `FLASK_RUN_PORT`) to access the Radiojoe web interface.  If running from another machine on the network, use the machines ip address.

## Automating with Crontab

Since both run from the same script, consider using cron to run the `run_recorder.sh` on boot.

1. Open the crontab editor:

   ```bash
   crontab -e
   ```

2. Add the following entry to start the recorder on boot:

   ```text
   @reboot /path/to/your/project/run_recorder.sh >> /path/to/your/project/radiojoe.log 2>&1 &
   ```

Replace `/path/to/your/project` with the actual path to your project directory.

## Troubleshooting

- **Application not running:** Check the `radiojoe.log` file for any error messages.
- **Recordings not being created:**

  - Ensure ffmpeg is installed and accessible in your system's PATH.
  - Verify that the stream URLs in your `config.json` are correct and accessible.
  - Check that the virtual environment is activated.

- **Web interface not accessible:**

  - Inspect logs for any apparent traceback, and ensure the program is running.

## Contributing

Feel free to fork this project and submit pull requests with any improvements or bug fixes.
