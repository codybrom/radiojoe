import recorder
import os
import json
import time
from datetime import datetime, timedelta
import pytz
import threading
import http.server
import socketserver
import logging
from pydub import AudioSegment
from pydub.generators import Sine
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Generate a simple MP3 file with a sine wave tone


def generate_tone_mp3(filename, duration=60, freq=440):
    sine_wave = Sine(freq).to_audio_segment(
        duration=duration*1000)  # duration in milliseconds
    sine_wave.export(filename, format="mp3")


# Generate the MP3 file
mp3_filename = 'test_tone.mp3'
generate_tone_mp3(mp3_filename)

# Simulated stream server


class SimulatedStreamHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "audio/mpeg")
        self.send_header("icy-name", "Test Stream")
        self.send_header("icy-genre", "Test")
        self.end_headers()
        try:
            with open(mp3_filename, 'rb') as mp3_file:
                while True:  # Loop the MP3 file continuously
                    chunk = mp3_file.read(4096)
                    if not chunk:
                        # Start over from the beginning of the file
                        mp3_file.seek(0)
                        continue
                    self.wfile.write(chunk)
                    time.sleep(0.1)  # Small delay to control streaming rate
        except BrokenPipeError:
            logging.info("Client disconnected. This is expected behavior.")
        except Exception as e:
            logging.error(f"Error in stream simulation: {e}")


def run_simulated_stream_server():
    with socketserver.TCPServer(("", 8000), SimulatedStreamHandler) as httpd:
        logging.info("Serving simulated MP3 stream at port 8000")
        httpd.serve_forever()


# Start the simulated stream server in a separate thread
stream_thread = threading.Thread(target=run_simulated_stream_server)
# This allows the thread to be terminated when the main program exits
stream_thread.daemon = True
stream_thread.start()

# Create a test configuration
test_config = {
    "shows": [
        {
            "name": "Test Show 1",
            "url": "http://localhost:8000",
            "day": (datetime.now() + timedelta(minutes=1)).strftime("%A"),
            "time": (datetime.now() + timedelta(minutes=1)).strftime("%I:%M %p"),
            "timezone": "America/Chicago",
            "duration": 30,
            "artist": "Test Artist",
            "album": "Test Album",
            "genre": "Test Genre"
        },
        {
            "name": "Test Show 2",
            "url": "http://localhost:8000",
            "day": (datetime.now() + timedelta(hours=1, minutes=2)).strftime("%A"),
            "time": (datetime.now() + timedelta(hours=1, minutes=2)).strftime("%I:%M %p"),
            "timezone": "America/New_York",
            "duration": 30,
            "artist": "Test Artist 2",
            "album": "Test Album 2",
            "genre": "Test Genre 2"
        }
    ]
}

# Write the test configuration to a file
with open('test_config.json', 'w') as f:
    json.dump(test_config, f, indent=2)

# Set environment variables
os.environ['RADIOJOE_BASE_DIR'] = os.getcwd()
os.environ['RADIOJOE_CONFIG_FILE'] = os.path.join(
    os.getcwd(), 'test_config.json')
os.environ['RADIOJOE_OUTPUT_DIR'] = os.path.join(
    os.getcwd(), 'test_recordings')
os.environ['RADIOJOE_LOG_FILE'] = os.path.join(
    os.getcwd(), 'test_recorder.log')

# Ensure the output directory exists
os.makedirs(os.environ['RADIOJOE_OUTPUT_DIR'], exist_ok=True)

# Import and run the recorder

if __name__ == "__main__":
    logging.info("Starting recorder test...")
    recorder_thread = threading.Thread(
        target=recorder.schedule_recordings, args=(test_config,))
    recorder_thread.start()

    # Run for 5 minutes
    for _ in range(30):  # 30 * 10 seconds = 5 minutes
        time.sleep(10)
        logging.info("Test still running...")

    logging.info("Test complete. Checking results...")

    # Check for recorded files
    recorded_files = os.listdir(os.environ['RADIOJOE_OUTPUT_DIR'])
    logging.info(f"Recorded files: {recorded_files}")

    if len(recorded_files) == 2:
        logging.info("Test PASSED: Both shows were recorded.")
    else:
        logging.warning(f"Test FAILED: Expected 2 recordings, but found {
                        len(recorded_files)}.")

    logging.info("Cleaning up test files...")

    # Clean up the test MP3 file
    if os.path.exists(mp3_filename):
        os.remove(mp3_filename)
        logging.info(f"Removed {mp3_filename}")

    # Remove the test configuration file
    if os.path.exists('test_config.json'):
        os.remove('test_config.json')
        logging.info("Removed test_config.json")

    # Remove the test recordings directory
    if os.path.exists(os.environ['RADIOJOE_OUTPUT_DIR']):
        shutil.rmtree(os.environ['RADIOJOE_OUTPUT_DIR'])
        logging.info(f"Removed directory: {os.environ['RADIOJOE_OUTPUT_DIR']}")

    # Remove the test log file
    if os.path.exists(os.environ['RADIOJOE_LOG_FILE']):
        os.remove(os.environ['RADIOJOE_LOG_FILE'])
        logging.info(f"Removed {os.environ['RADIOJOE_LOG_FILE']}")

    logging.info("Cleanup complete. Shutting down...")

    # Note: You might want to implement a clean shutdown method in recorder.py
    # For now, we'll just wait a bit to allow any ongoing recordings to finish
    time.sleep(4)

    # Force quit the program
    os._exit(0)
