import json
from datetime import datetime, timedelta
import pytz
import requests
import concurrent.futures
import calendar
from collections import defaultdict


def load_config(filename):
    with open(filename, 'r') as f:
        return json.load(f)


def test_link(url, retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    for attempt in range(retries):
        try:
            response = requests.get(
                url, timeout=10, headers=headers, stream=True)
            content_type = response.headers.get('Content-Type', '')

            if response.status_code == 200:
                if 'audio' in content_type or 'video' in content_type or 'application/octet-stream' in content_type:
                    return "✅", f"Status: {response.status_code}, Content-Type: {content_type}"
                else:
                    return "❓", f"Status: {response.status_code}, Content-Type: {content_type} (Not an audio stream?)"
            else:
                return "❌", f"Status: {response.status_code}, Content-Type: {content_type}"
        except requests.RequestException as e:
            if attempt == retries - 1:
                return "❌", str(e)
    return "❌", "Max retries reached"


def get_next_show_datetime(show, now):
    show_day = show['day']
    show_time = show['time']
    show_tz = pytz.timezone(show['timezone'])

    # Parse the show time
    show_time = datetime.strptime(show_time, '%I:%M %p').time()

    # Find the next occurrence of the show
    days_ahead = (list(calendar.day_name).index(
        show_day) - now.weekday() + 7) % 7
    next_show_date = now.date() + timedelta(days=days_ahead)
    show_datetime = datetime.combine(next_show_date, show_time)
    show_datetime = show_tz.localize(show_datetime)
    show_datetime_central = show_datetime.astimezone(
        pytz.timezone('America/Chicago'))

    # If the show is in the past, move to next week
    if show_datetime_central < now:
        show_datetime_central += timedelta(days=7)
        show_datetime = show_datetime + timedelta(days=7)

    return show_datetime_central, show_datetime


def get_next_7_days_schedule(config):
    now = datetime.now(pytz.timezone('America/Chicago'))
    end_date = now + timedelta(days=7)

    next_7_days = defaultdict(list)
    for show in config['shows']:
        next_show_datetime_central, next_show_datetime_original = get_next_show_datetime(
            show, now)
        if next_show_datetime_central < end_date:
            day_key = next_show_datetime_central.date()
            next_7_days[day_key].append(
                (show['name'], next_show_datetime_central, next_show_datetime_original, show['url'], show['timezone']))

    # Sort shows within each day
    for day in next_7_days:
        next_7_days[day].sort(key=lambda x: x[1])

    # Sort days
    sorted_days = sorted(next_7_days.items())

    return sorted_days


def print_schedule(schedule):
    print("Upcoming Recordings for the Next 7 Days:")
    print(f"(From {datetime.now(pytz.timezone('America/Chicago')).strftime('%A, %B %d, %Y')} to {
          (datetime.now(pytz.timezone('America/Chicago')) + timedelta(days=7)).strftime('%A, %B %d, %Y')})\n")
    print("Testing links... This may take a moment.\n")

    all_shows = [show for day in schedule for show in day[1]]

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_show = {executor.submit(
            test_link, show[3]): show for show in all_shows}

        results = {}
        for future in concurrent.futures.as_completed(future_to_show):
            show = future_to_show[future]
            try:
                link_status, status_info = future.result(timeout=15)
            except concurrent.futures.TimeoutError:
                link_status, status_info = "⏳", "Timeout"
            results[show] = (link_status, status_info)

    for day, shows in schedule:
        print(f"{day.strftime('%A, %B %d, %Y')}")
        for show in shows:
            show_name, show_datetime_central, show_datetime_original, url, timezone = show
            link_status, status_info = results[show]
            print(f"{link_status} {show_name}")
            print(f"   Local time (CDT): {
                  show_datetime_central.strftime('%I:%M %p')}")
            print(f"   Original time ({timezone}): {
                  show_datetime_original.strftime('%I:%M %p')}")
            print(f"   {url}")
            print(f"   {status_info}\n")
        print()  # Extra newline between days


if __name__ == "__main__":
    config = load_config('config.json')
    schedule = get_next_7_days_schedule(config)
    print_schedule(schedule)
