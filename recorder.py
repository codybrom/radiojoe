import os
import json
import schedule
import time
from datetime import datetime, timedelta
import pytz
import subprocess
import logging
import threading
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON

# Get the base directory from environment variable, with a fallback
BASE_DIR = os.getenv('RADIOJOE_BASE_DIR',
                     os.path.dirname(os.path.abspath(__file__)))

# Configure logging
log_file = os.getenv('RADIOJOE_LOG_FILE',
                     os.path.join(BASE_DIR, 'recorder.log'))
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

config_path = os.getenv('RADIOJOE_CONFIG_FILE',
                        os.path.join(BASE_DIR, 'config.json'))


def save_config(config):
    config_path = os.getenv('RADIOJOE_CONFIG_FILE',
                            os.path.join(BASE_DIR, 'config.json'))
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def get_next_7_days_schedule(config):
    now = datetime.now(pytz.timezone('America/Chicago'))
    end_date = now + timedelta(days=7)

    schedule = []
    for day in range(7):
        current_date = now.date() + timedelta(days=day)
        day_shows = []
        for show in config['shows']:
            show_day, show_time = convert_to_central(
                show['time'], show['day'], show['timezone'])
            if show_day == current_date.strftime("%A"):
                show_datetime = datetime.combine(
                    current_date, datetime.strptime(show_time, "%H:%M").time())
                day_shows.append({
                    'name': show['name'],
                    'time': show_datetime,
                    'timezone': show['timezone']
                })
        if day_shows:
            schedule.append((current_date, sorted(
                day_shows, key=lambda x: x['time'])))

    return schedule


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


def record_stream(name, url, duration, output_dir, metadata):
    def _record():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(output_dir, f'{name}_{timestamp}.mp3')

        # FFmpeg command to capture the stream
        command = [
            'ffmpeg',
            '-i', url,
            '-t', str(duration),
            '-acodec', 'libmp3lame',
            output_file
        ]

        try:
            # Log the start of the recording
            logging.info(f"Starting recording {name}: {url} for {
                         duration} seconds, saving to {output_file}")

            # Run the command
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait for the process to complete
            stdout, stderr = process.communicate()

            # Check for errors
            if process.returncode != 0:
                raise Exception(f"ffmpeg exited with error code {
                                process.returncode}: {stderr.decode()}")

            logging.info(f'Finished recording {name}: {
                         url} for {duration} seconds')

            # Add metadata only if the file exists
            if os.path.exists(output_file):
                try:
                    audio = MP3(output_file, ID3=ID3)

                    # Add ID3 tag if it doesn't exist
                    try:
                        audio.add_tags()
                    except mutagen.id3.error:
                        pass

                    # Format the title as "Show Name - Month Day, Year - HH:MM AM/PM Timezone"
                    recording_time = datetime.now(pytz.timezone(
                        metadata.get('timezone', 'America/Chicago')))
                    formatted_title = f"{
                        name} - {recording_time.strftime('%B %d, %Y - %I:%M %p %Z')}"

                    audio.tags.add(TIT2(encoding=3, text=formatted_title))
                    audio.tags.add(
                        TPE1(encoding=3, text=metadata.get('artist', 'Various Artists')))
                    audio.tags.add(TALB(encoding=3, text=metadata.get(
                        'album', 'Radiojoe Recordings')))
                    if 'genre' in metadata:
                        audio.tags.add(
                            TCON(encoding=3, text=metadata['genre']))

                    audio.save()

                    logging.info(f'Added metadata to {output_file}')
                except Exception as e:
                    logging.error(f'Error adding metadata to {
                                  output_file}: {e}')
            else:
                logging.error(f'Recording file not found: {output_file}')
        except Exception as e:
            logging.error(f'Error recording {name}: {url} - {e}')

    # Create and start the recording thread
    recording_thread = threading.Thread(target=_record)
    recording_thread.start()

# Schedule recordings


def schedule_recordings(config):
    output_dir = os.getenv('RADIOJOE_OUTPUT_DIR',
                           os.path.join(BASE_DIR, 'recordings'))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    default_metadata = config.get('default_metadata', {})

    for show in config['shows']:
        day_of_week, time_of_day = convert_to_central(
            show['time'], show['day'], show['timezone'])

        # Combine default metadata with show-specific metadata
        metadata = default_metadata.copy()
        metadata.update(
            {k: show[k] for k in ['artist', 'album', 'genre', 'timezone'] if k in show})

        # Schedule the recording
        if day_of_week == "Monday":
            schedule.every().monday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir, metadata)
        elif day_of_week == "Tuesday":
            schedule.every().tuesday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir, metadata)
        elif day_of_week == "Wednesday":
            schedule.every().wednesday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir, metadata)
        elif day_of_week == "Thursday":
            schedule.every().thursday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir, metadata)
        elif day_of_week == "Friday":
            schedule.every().friday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir, metadata)
        elif day_of_week == "Saturday":
            schedule.every().saturday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir, metadata)
        elif day_of_week == "Sunday":
            schedule.every().sunday.at(time_of_day).do(
                record_stream, show['name'], show['url'], show['duration'], output_dir, metadata)

        # Log the scheduling
        logging.info(f"Scheduled recording for {show['name']} on {
                     day_of_week} at {time_of_day} Central Time")

    while True:
        schedule.run_pending()
        time.sleep(1)


def load_config():
    with open(config_path, 'r') as f:
        return json.load(f)


def recheck_config():
    while True:
        logging.info('Checking configuration...')
        now = datetime.now(pytz.timezone('America/Chicago'))
        config = load_config()  # Load the configuration again
        upcoming_recordings = [
            (show['name'], *convert_to_central(show['time'],
             show['day'], show['timezone']))
            for show in config['shows']
        ]
        upcoming_recordings = sorted(
            [r for r in upcoming_recordings if datetime.strptime(
                r[2], "%H:%M").time() > now.time()],
            key=lambda x: datetime.strptime(x[2], "%H:%M").time()
        )

        # Only recheck if no recordings are starting within the next 15 minutes
        if not upcoming_recordings or (datetime.combine(now.date(), datetime.strptime(upcoming_recordings[0][2], "%H:%M").time()) - now).total_seconds() > 900:
            schedule.clear()  # Clear the existing schedule

            # Schedule recordings with the new configuration
            schedule_recordings(config)

        # Sleep for 1 hour before next check
        time.sleep(3600)  # 1 hour in seconds


if __name__ == "__main__":
    logging.info('Starting the recorder script')

    config = load_config()

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(
        target=schedule_recordings, args=(config,))
    scheduler_thread.start()

    # Start the recheck configuration task in a separate thread
    recheck_thread = threading.Thread(target=recheck_config)
    recheck_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        # You might want to add cleanup code here
