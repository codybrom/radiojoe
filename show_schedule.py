import json
from datetime import datetime, timedelta
import pytz
import requests
import concurrent.futures
import calendar


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


def get_next_7_days_schedule(config):
    now = datetime.now(pytz.timezone('America/Chicago'))
    next_7_days = []
    end_date = now + timedelta(days=7)

    for show in config['shows']:
        show_day = show['day']
        show_time = show['time']
        show_tz = pytz.timezone(show['timezone'])

        # Find the next occurrence of the show
        days_ahead = (list(calendar.day_name).index(
            show_day) - now.weekday() + 7) % 7
        next_show_date = now.date() + timedelta(days=days_ahead)
        show_datetime = datetime.combine(
            next_show_date, datetime.strptime(show_time, '%I:%M %p').time())
        show_datetime = show_tz.localize(show_datetime)
        show_datetime_central = show_datetime.astimezone(
            pytz.timezone('America/Chicago'))

        # If the show is in the past, move to next week
        if show_datetime_central < now:
            show_datetime_central += timedelta(days=7)

        # Add the show if it's within the next 7 days
        if show_datetime_central < end_date:
            next_7_days.append(
                (show['name'], show_datetime_central, show['url']))

    next_7_days.sort(key=lambda x: x[1])
    return next_7_days


def print_schedule(schedule):
    print("Upcoming Recordings for the Next 7 Days:")
    print(f"(From {datetime.now(pytz.timezone('America/Chicago')).strftime('%A, %B %d, %Y')} to {
          (datetime.now(pytz.timezone('America/Chicago')) + timedelta(days=7)).strftime('%A, %B %d, %Y')})\n")
    print("Testing links... This may take a moment.\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_show = {executor.submit(
            test_link, show[2]): show for show in schedule}

        for future in concurrent.futures.as_completed(future_to_show):
            show = future_to_show[future]
            show_name, show_datetime, url = show
            try:
                link_status, status_info = future.result(timeout=15)
            except concurrent.futures.TimeoutError:
                link_status, status_info = "⏳", "Timeout"

            print(f"{link_status} {show_name}")
            print(f"   {show_datetime.strftime(
                '%A, %B %d, %Y at %I:%M %p %Z')}")
            print(f"   {url}")
            print(f"   {status_info}\n")


if __name__ == "__main__":
    config = load_config('config.json')
    schedule = get_next_7_days_schedule(config)
    print_schedule(schedule)
