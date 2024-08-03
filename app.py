from collections import defaultdict
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import os
from datetime import datetime, timedelta
import pytz
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.id3._frames import COMM
from mutagen.id3._frames import TYER
from mutagen.id3._frames import TCON
from mutagen.id3._frames import TALB
from mutagen.id3._frames import TPE1
from mutagen.id3._frames import TIT2
from recorder import load_config, save_config, convert_to_central, get_next_7_days_schedule
import psutil
import shutil
from recorder import load_config, get_next_7_days_schedule
import humanize

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_recordings():
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))
    recordings = []
    for file in os.listdir(recordings_dir):
        if file.endswith('.mp3'):
            recordings.append(file)
    return sorted(recordings, reverse=True)


@app.route('/')
def index():
    config = load_config()
    shows = config['shows']

    # Add the config index to each show
    for i, show in enumerate(shows):
        show['config_index'] = i

    # Get current time in Chicago (America/Chicago)
    chicago_tz = pytz.timezone('America/Chicago')
    now = datetime.now(chicago_tz)

    # Function to get the next occurrence of a show
    def get_next_occurrence(show):
        show_time = datetime.strptime(show['time'], '%I:%M %p').time()
        show_day = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                    'Friday', 'Saturday', 'Sunday'].index(show['day'])
        show_tz = pytz.timezone(show['timezone'])

        # Convert show time to Chicago time
        show_datetime = datetime.combine(now.date(), show_time)
        show_datetime = show_tz.localize(show_datetime).astimezone(chicago_tz)

        # Adjust the date to the next occurrence
        days_ahead = show_day - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and now.time() > show_datetime.time()):
            days_ahead += 7
        next_show = show_datetime + timedelta(days=days_ahead)

        return next_show

    # Sort shows based on their next occurrence
    sorted_shows = sorted(shows, key=get_next_occurrence)

    return render_template('index.html', shows=sorted_shows, current_time=now)


@app.route('/recordings/<path:filename>')
def serve_recording(filename):
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))
    return send_from_directory(recordings_dir, filename)


def get_mp3_tags(file_path):
    audio = MP3(file_path, ID3=ID3)
    tags = {}
    if audio.tags:
        tags['title'] = str(audio.tags.get('TIT2', [''])[0])
        tags['artist'] = str(audio.tags.get('TPE1', [''])[0])
        tags['album'] = str(audio.tags.get('TALB', [''])[0])
        tags['genre'] = str(audio.tags.get('TCON', [''])[0])
        tags['year'] = str(audio.tags.get('TYER', [''])[0])
        tags['comment'] = str(audio.tags.get('COMM', [''])[0])
    return tags


@app.route('/recordings')
def recordings():
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))
    recordings = []
    for file in os.listdir(recordings_dir):
        if file.endswith('.mp3'):
            file_path = os.path.join(recordings_dir, file)
            tags = get_mp3_tags(file_path)
            date = datetime.fromtimestamp(os.path.getmtime(
                file_path)).strftime('%Y-%m-%d %H:%M:%S')
            recordings.append({'filename': file, 'tags': tags, 'date': date})

    # Sort recordings by date (newest first)
    recordings.sort(key=lambda x: x['date'], reverse=True)

    return render_template('recordings.html', recordings=recordings)


@app.route('/edit_tags/<path:filename>', methods=['GET', 'POST'])
def edit_tags(filename):
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))
    file_path = os.path.join(recordings_dir, filename)

    if request.method == 'POST':
        audio = MP3(file_path, ID3=ID3)
        if audio.tags is None:
            audio.tags = ID3()

        audio.tags['TIT2'] = TIT2(encoding=3, text=request.form['title'])
        audio.tags['TPE1'] = TPE1(encoding=3, text=request.form['artist'])
        audio.tags['TALB'] = TALB(encoding=3, text=request.form['album'])
        audio.tags['TCON'] = TCON(encoding=3, text=request.form['genre'])
        audio.tags['TYER'] = TYER(encoding=3, text=request.form['year'])
        audio.tags['COMM'] = COMM(
            encoding=3, lang='eng', desc='comment', text=request.form['comment'])

        audio.save()
        return redirect(url_for('recordings'))

    tags = get_mp3_tags(file_path)
    return render_template('edit_tags.html', filename=filename, tags=tags)


@app.route('/delete_recording/<path:filename>', methods=['POST'])
def delete_recording(filename):
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))
    file_path = os.path.join(recordings_dir, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"success": True, "message": "Recording deleted successfully"})
    else:
        return jsonify({"success": False, "message": "Recording not found"}), 404

# Add a new route for exporting all recordings


@app.route('/export_recordings', methods=['GET'])
def export_recordings():
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))
    recordings = []
    for file in os.listdir(recordings_dir):
        if file.endswith('.mp3'):
            file_path = os.path.join(recordings_dir, file)
            tags = get_mp3_tags(file_path)
            date = datetime.fromtimestamp(os.path.getmtime(
                file_path)).strftime('%Y-%m-%d %H:%M:%S')
            recordings.append({
                'filename': file,
                'title': tags.get('title', ''),
                'artist': tags.get('artist', ''),
                'album': tags.get('album', ''),
                'genre': tags.get('genre', ''),
                'year': tags.get('year', ''),
                'date': date
            })

    return jsonify(recordings)


@app.route('/add_show', methods=['GET', 'POST'])
def add_show():
    if request.method == 'POST':
        config = load_config()
        new_show = {
            'name': request.form['name'],
            'url': request.form['url'],
            'day': request.form['day'],
            'time': request.form['time'],
            'timezone': request.form['timezone'],
            'duration': int(request.form['duration']),
            'artist': request.form['artist'],
            'album': request.form['album'],
            'genre': request.form['genre']
        }
        config['shows'].append(new_show)
        save_config(config)
        return redirect(url_for('index'))
    return render_template('add_show.html')


@app.route('/edit_show/<int:index>', methods=['GET', 'POST'])
def edit_show(index):
    config = load_config()
    if index < 0 or index >= len(config['shows']):
        return "Show not found", 404

    show = config['shows'][index]

    if request.method == 'POST':
        if 'delete' in request.form:
            del config['shows'][index]
            save_config(config)
            return redirect(url_for('index'))
        else:
            show['name'] = request.form['name']
            show['url'] = request.form['url']
            show['day'] = request.form['day']

            # Convert start and end times from HH:MM format to HH:MM AM/PM format
            start_time = datetime.strptime(request.form['start_time'], '%H:%M')
            end_time = datetime.strptime(request.form['end_time'], '%H:%M')

            show['time'] = start_time.strftime('%I:%M %p')

            # Calculate duration in seconds
            duration = end_time - start_time
            if duration.days < 0:  # If end time is on the next day
                duration += timedelta(days=1)
            show['duration'] = int(duration.total_seconds())

            show['timezone'] = request.form['timezone']
            show['artist'] = request.form['artist']
            show['album'] = request.form['album']
            show['genre'] = request.form['genre']
            save_config(config)
            return redirect(url_for('index'))

    # Convert time from HH:MM AM/PM format to HH:MM format for the form
    time_obj = datetime.strptime(show['time'], '%I:%M %p')
    show['start_time'] = time_obj.strftime('%H:%M')

    # Calculate end time based on duration
    end_time = time_obj + timedelta(seconds=show['duration'])
    show['end_time'] = end_time.strftime('%H:%M')

    return render_template('edit_show.html', show=show, index=index)


@app.route('/status')
def status():
    config = load_config()
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))

    # Get disk usage
    total, used, free = shutil.disk_usage(recordings_dir)
    disk_usage = {
        'total': f"{total // (2**30)} GB",
        'used': f"{used // (2**30)} GB",
        'free': f"{free // (2**30)} GB",
        'percent': f"{used * 100 // total}%"
    }

    # Get CPU and memory usage
    cpu_usage = f"{psutil.cpu_percent()}%"
    memory = psutil.virtual_memory()
    memory_usage = f"{memory.percent}%"

    # Get the last recorded file
    recordings = [f for f in os.listdir(recordings_dir) if f.endswith('.mp3')]
    last_recording = max(recordings, key=lambda f: os.path.getmtime(
        os.path.join(recordings_dir, f))) if recordings else None
    if last_recording:
        last_recording_time = datetime.fromtimestamp(
            os.path.getmtime(os.path.join(recordings_dir, last_recording)))
        last_recording_time = pytz.timezone(
            'America/Chicago').localize(last_recording_time)
        last_recording = f"{
            last_recording} - {last_recording_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"

    # Get the next scheduled recording
    schedule = get_next_7_days_schedule(config)
    next_recording = None
    next_recording_time = None
    now = pytz.timezone('America/Chicago').localize(datetime.now())
    for day, shows in schedule:
        for show in shows:
            show_time = pytz.timezone(
                'America/Chicago').localize(show['time'].replace(tzinfo=None))
            if show_time > now:
                next_recording_time = show_time
                next_recording = f"{
                    show['name']} - {show_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                break
        if next_recording:
            break

    # Calculate relative time for next recording
    next_recording_relative = None
    if next_recording_time:
        next_recording_relative = humanize.naturaltime(
            next_recording_time, when=now)

    status_info = {
        'disk_usage': disk_usage,
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage,
        'last_recording': last_recording or "No recordings yet",
        'next_recording': next_recording or "No upcoming recordings",
        'next_recording_relative': next_recording_relative or "N/A",
        'total_recordings': len(recordings)
    }

    return render_template('status.html', status=status_info)


if __name__ == '__main__':
    app.run(debug=True)
