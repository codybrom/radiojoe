from collections import defaultdict
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import json
import os
from datetime import datetime, timedelta
import pytz
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON
from recorder import load_config, save_config, convert_to_central, get_next_7_days_schedule

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
    local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('index.html', shows=config['shows'], local_time=local_time)


@app.route('/recordings/<path:filename>')
def serve_recording(filename):
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))
    return send_from_directory(recordings_dir, filename)


def get_mp3_tags(file_path):
    audio = MP3(file_path, ID3=ID3)
    tags = {}
    if audio.tags:
        tags['title'] = audio.tags.get('TIT2', [''])[0]
        tags['artist'] = audio.tags.get('TPE1', [''])[0]
        tags['album'] = audio.tags.get('TALB', [''])[0]
        tags['genre'] = audio.tags.get('TCON', [''])[0]
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
            recordings.append({'filename': file, 'tags': tags})
    return render_template('recordings.html', recordings=recordings)


@app.route('/edit_tags/<path:filename>', methods=['GET', 'POST'])
def edit_tags(filename):
    recordings_dir = os.getenv(
        'RADIOJOE_OUTPUT_DIR', os.path.join(BASE_DIR, 'recordings'))
    file_path = os.path.join(recordings_dir, filename)

    if request.method == 'POST':
        audio = MP3(file_path, ID3=ID3)
        if not audio.tags:
            audio.add_tags()

        audio.tags['TIT2'] = TIT2(encoding=3, text=request.form['title'])
        audio.tags['TPE1'] = TPE1(encoding=3, text=request.form['artist'])
        audio.tags['TALB'] = TALB(encoding=3, text=request.form['album'])
        audio.tags['TCON'] = TCON(encoding=3, text=request.form['genre'])

        audio.save()
        return redirect(url_for('recordings'))

    tags = get_mp3_tags(file_path)
    return render_template('edit_tags.html', filename=filename, tags=tags)


@app.route('/schedule')
def schedule():
    config = load_config()
    shows = config['shows']

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

    return render_template('schedule.html', shows=sorted_shows, current_time=now)


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
    if request.method == 'POST':
        if 'delete' in request.form:
            del config['shows'][index]
            save_config(config)
            return redirect(url_for('index'))
        else:
            show = config['shows'][index]
            show['name'] = request.form['name']
            show['url'] = request.form['url']
            show['day'] = request.form['day']
            show['time'] = request.form['time']
            show['timezone'] = request.form['timezone']
            show['duration'] = int(request.form['duration'])
            show['artist'] = request.form['artist']
            show['album'] = request.form['album']
            show['genre'] = request.form['genre']
            save_config(config)
            return redirect(url_for('index'))
    show = config['shows'][index]
    return render_template('edit_show.html', show=show, index=index)


@app.route('/status')
def status():
    # You'll need to implement logic to get the current status
    # This could include information about ongoing recordings, last successful recording, etc.
    status_info = {
        'last_recording': 'Show A - 2023-07-20 15:00',
        'next_recording': 'Show B - 2023-07-21 10:00',
        'disk_space': '500GB free'
    }
    return render_template('status.html', status=status_info)


if __name__ == '__main__':
    app.run(debug=True)
