import os
import json
import schedule
import time
from datetime import datetime, timedelta
import pytz
import subprocess
import logging
import threading
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.id3._frames import TPE1, TCON, TIT2, TALB


# Load configuration
def load_config():
    config_path = os.getenv("RADIOJOE_CONFIG_FILE", "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}. Exiting.")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file at {config_path}. Exiting.")
        exit(1)


config = load_config()


# Configuration parameters from config file
BASE_DIR = config.get("base_dir", os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = config.get("log_file", os.path.join(BASE_DIR, "recorder.log"))
OUTPUT_DIR = config.get("output_dir", os.path.join(BASE_DIR, "recordings"))
CONFIG_FILE = config.get("config_file", "config.json")
STATUS_FILE = config.get("status_file", "radiojoe_status.json")


# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


active_recordings = []


def update_status(recordings):
    global active_recordings
    active_recordings = recordings
    status = {
        "last_updated": datetime.now().isoformat(),
        "active_recordings": active_recordings,
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f)


def save_config(config):
    config_path = os.getenv("RADIOJOE_CONFIG_FILE", "config.json")
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_next_7_days_schedule(config):
    now = datetime.now(pytz.timezone("America/Chicago"))
    end_date = now + timedelta(days=7)

    schedule = []
    for day in range(7):
        current_date = now.date() + timedelta(days=day)
        day_shows = []
        for show in config["shows"]:
            show_day, show_time = convert_to_central(
                show["time"], show["day"], show["timezone"]
            )
            if show_day == current_date.strftime("%A"):
                show_datetime = datetime.combine(
                    current_date, datetime.strptime(show_time, "%H:%M").time()
                )
                day_shows.append(
                    {
                        "name": show["name"],
                        "time": show_datetime,
                        "timezone": show["timezone"],
                    }
                )
        if day_shows:
            schedule.append((current_date, sorted(day_shows, key=lambda x: x["time"])))

    return schedule


def convert_to_central(time_str, day, from_tz_str):
    local_tz = pytz.timezone("America/Chicago")  # Central Time
    from_tz = pytz.timezone(from_tz_str)

    # Get the current date
    now = datetime.now(local_tz)

    # Find the next occurrence of the specified day
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"{name}_{timestamp}.mp3")

        # FFmpeg command to capture the stream
        command = [
            "ffmpeg",
            "-i",
            url,
            "-t",
            str(duration),
            "-acodec",
            "libmp3lame",
            output_file,
        ]

        global active_recordings
        active_recordings.append(name)
        update_status(active_recordings)
        try:
            # Log the start of the recording
            logging.info(
                f"Starting recording {name}: {url} for {
                         duration} seconds, saving to {output_file}"
            )

            # Run the command
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Wait for the process to complete
            stdout, stderr = process.communicate()

            # Check for errors
            if process.returncode != 0:
                raise Exception(
                    f"ffmpeg exited with error code {
                                process.returncode}: {stderr.decode()}"
                )

            logging.info(
                f"Finished recording {name}: {
                         url} for {duration} seconds"
            )

            # Add metadata only if the file exists
            if os.path.exists(output_file):
                try:
                    audio = MP3(output_file, ID3=ID3)

                    # Add ID3 tag if it doesn't exist
                    if audio.tags is None:
                        audio.tags = ID3()

                    # NOTE: Using a more generic way to access timezone aware datetimes.
                    recording_time = datetime.now(
                        pytz.timezone(metadata.get("timezone", "America/Chicago"))
                    )

                    # Format the title as "Show Name - Month Day, Year - HH:MM AM/PM Timezone"
                    formatted_title = f"{
                        name} - {recording_time.strftime('%B %d, %Y - %I:%M %p %Z')}"

                    audio.tags.add(TIT2(encoding=3, text=formatted_title))
                    audio.tags.add(
                        TPE1(encoding=3, text=metadata.get("artist", "Various Artists"))
                    )
                    audio.tags.add(
                        TALB(
                            encoding=3,
                            text=metadata.get("album", "Radiojoe Recordings"),
                        )
                    )
                    if "genre" in metadata:
                        audio.tags.add(TCON(encoding=3, text=metadata["genre"]))

                    audio.save()

                    logging.info(f"Added metadata to {output_file}")
                except Exception as e:
                    logging.error(
                        f"Error adding metadata to {
                                  output_file}: {e}"
                    )
            else:
                logging.error(f"Recording file not found: {output_file}")
        except Exception as e:
            logging.error(f"Error recording {name}: {url} - {e}")
        finally:
            active_recordings.remove(name)
            update_status(active_recordings)

    # Create and start the recording thread
    recording_thread = threading.Thread(target=_record)
    recording_thread.start()


# Schedule recordings
def schedule_recordings(config):
    output_dir = OUTPUT_DIR
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    default_metadata = config.get("default_metadata", {})

    for show in config["shows"]:
        day_of_week, time_of_day = convert_to_central(
            show["time"], show["day"], show["timezone"]
        )

        # Combine default metadata with show-specific metadata
        metadata = default_metadata.copy()
        metadata.update(
            {k: show[k] for k in ["artist", "album", "genre", "timezone"] if k in show}
        )

        # Schedule the recording
        if day_of_week == "Monday":
            schedule.every().monday.at(time_of_day).do(
                record_stream,
                show["name"],
                show["url"],
                show["duration"],
                output_dir,
                metadata,
            )
        elif day_of_week == "Tuesday":
            schedule.every().tuesday.at(time_of_day).do(
                record_stream,
                show["name"],
                show["url"],
                show["duration"],
                output_dir,
                metadata,
            )
        elif day_of_week == "Wednesday":
            schedule.every().wednesday.at(time_of_day).do(
                record_stream,
                show["name"],
                show["url"],
                show["duration"],
                output_dir,
                metadata,
            )
        elif day_of_week == "Thursday":
            schedule.every().thursday.at(time_of_day).do(
                record_stream,
                show["name"],
                show["url"],
                show["duration"],
                output_dir,
                metadata,
            )
        elif day_of_week == "Friday":
            schedule.every().friday.at(time_of_day).do(
                record_stream,
                show["name"],
                show["url"],
                show["duration"],
                output_dir,
                metadata,
            )
        elif day_of_week == "Saturday":
            schedule.every().saturday.at(time_of_day).do(
                record_stream,
                show["name"],
                show["url"],
                show["duration"],
                output_dir,
                metadata,
            )
        elif day_of_week == "Sunday":
            schedule.every().sunday.at(time_of_day).do(
                record_stream,
                show["name"],
                show["url"],
                show["duration"],
                output_dir,
                metadata,
            )

        # Log the scheduling
        logging.info(
            f"Scheduled recording for {show['name']} on {
                     day_of_week} at {time_of_day} Central Time"
        )

    while True:
        schedule.run_pending()
        time.sleep(1)


def recheck_config():
    while True:
        logging.info("Checking configuration...")
        chicago_tz = pytz.timezone("America/Chicago")
        now = datetime.now(chicago_tz)  # Timezone aware

        config = load_config()  # Load the configuration again

        upcoming_recordings = [
            (
                show["name"],
                *convert_to_central(show["time"], show["day"], show["timezone"]),
            )
            for show in config["shows"]
        ]
        upcoming_recordings = sorted(
            [
                r
                for r in upcoming_recordings
                if datetime.strptime(r[2], "%H:%M").time() > now.time()
            ],
            key=lambda x: datetime.strptime(x[2], "%H:%M").time(),
        )

        # Only recheck if no recordings are starting within the next 15 minutes
        if not upcoming_recordings:
            schedule.clear()
            schedule_recordings(config)
            time.sleep(3600)
            continue

        next_recording_time_str = upcoming_recordings[0][2]

        # Convert the string time to a datetime object
        next_recording_time_naive = datetime.strptime(
            next_recording_time_str, "%H:%M"
        ).time()
        next_recording_datetime_naive = datetime.combine(
            now.date(), next_recording_time_naive
        )
        next_recording_datetime_aware = chicago_tz.localize(
            next_recording_datetime_naive
        )

        time_difference = (next_recording_datetime_aware - now).total_seconds()

        if time_difference > 900:

            schedule.clear()  # Clear the existing schedule

            # Schedule recordings with the new configuration
            schedule_recordings(config)

        # Sleep for 1 hour before next check
        time.sleep(3600)  # 1 hour in seconds


if __name__ == "__main__":
    logging.info("Starting the recorder script")

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=schedule_recordings, args=(config,))
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
