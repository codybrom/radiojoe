import os
import json
import schedule
import time
from datetime import datetime, timedelta
import pytz
import subprocess
import logging
import sys

# Get the base directory from environment variable, with a fallback
BASE_DIR = os.getenv('RADIOJOE_BASE_DIR',
                     os.path.dirname(os.path.abspath(__file__)))

# Configure logging
log_file = os.getenv('RADIOJOE_LOG_FILE',
                     os.path.join(BASE_DIR, 'recorder.log'))
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def convert_to_central(time_str, day, from_tz_str):
    local_tz = pytz.timezone('America/Chicago')  # Central Time
    from_tz = pytz.timezone(from_tz_str)

    # Get the current date
    now = datetime.now(local_tz)

    # Find the next occurrence of the specified day
    days = ['Monday', 'Tuesday', 'Wednesday',
            'Thursday', 'Friday', 'Saturday', 'Sunday']
    target_day = days.index(day)
    current_day = now.weekday()
    days_ahead = target_day - current_day
    if days_ahead <= 0:
        days_ahead += 7

    target_date = now.date() + timedelta(days=days_ahead)

    # Combine target date and time into a single datetime string
    datetime_str = f"{target_date.strftime('%Y-%m-%d')} {time_str}"
    naive_time = datetime.strptime(datetime_str, "%Y-%m-%d %I:%M %p")
    from_time = from_tz.localize(naive_time)
    central_time = from_time.astimezone(local_tz)

    return central_time.strftime("%A"), central_time.strftime("%H:%M")

# Function to record the stream


def record_stream(name, url, duration, output_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'{name}_{timestamp}.mp3')

    # FFmpeg command to capture the stream
    command = [
        'ffmpeg',
        '-i', url,
        '-t', str(duration),
        '-acodec', 'copy',
        output_file
    ]

    # Log the start of the recording
    logging.info(f"Starting recording {name}: {url} for {
                 duration} seconds, saving to {output_file}")

    # Run the command
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for the process to complete
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        logging.info(f'Finished recording {name}: {
                     url} for {duration} seconds')
    else:
        logging.error(f'Error recording {name}: {url} - {stderr.decode()}')

# Schedule recordings


def schedule_recordings(config):
    output_dir = os.getenv('RADIOJOE_OUTPUT_DIR',
                           os.path.join(BASE_DIR, 'recordings'))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for show in config['shows']:
        day_of_week, time_of_day = convert_to_central(
            show['time'], show['day'], show['timezone'])

        # Schedule the recording
        if day_of_week == "Monday":
            schedule.every().monday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir)
        elif day_of_week == "Tuesday":
            schedule.every().tuesday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir)
        elif day_of_week == "Wednesday":
            schedule.every().wednesday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir)
        elif day_of_week == "Thursday":
            schedule.every().thursday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir)
        elif day_of_week == "Friday":
            schedule.every().friday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir)
        elif day_of_week == "Saturday":
            schedule.every().saturday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir)
        elif day_of_week == "Sunday":
            schedule.every().sunday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir)

        # Log the scheduling
        logging.info(f"Scheduled recording for {show['name']} on {
                     day_of_week} at {time_of_day} Central Time")

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    logging.info('Starting the recorder script')
    config_path = os.getenv('RADIOJOE_CONFIG_FILE',
                            os.path.join(BASE_DIR, 'config.json'))

    with open(config_path, 'r') as f:
        config = json.load(f)
    logging.info("Starting scheduler")
    schedule_recordings(config)
