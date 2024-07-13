import json
from datetime import datetime, timedelta
import pytz


def load_config(filename):
    with open(filename, 'r') as f:
        return json.load(f)


def get_next_7_days_schedule(config):
    now = datetime.now(pytz.timezone('America/Chicago')
                       )  # Current time in Central Time
    next_7_days = []

    for show in config['shows']:
        show_day = show['day']
        show_time = show['time']
        show_tz = pytz.timezone(show['timezone'])

        # Calculate the date and time for the next occurrence of the show
        for days_ahead in range(7):
            potential_date = now + timedelta(days=days_ahead)
            if potential_date.strftime("%A") == show_day:
                # Combine the date and time
                show_datetime_str = f"{
                    potential_date.strftime('%Y-%m-%d')} {show_time}"
                show_datetime = datetime.strptime(
                    show_datetime_str, '%Y-%m-%d %I:%M %p')

                # Localize and convert to Central Time
                show_datetime = show_tz.localize(show_datetime)
                show_datetime_central = show_datetime.astimezone(
                    pytz.timezone('America/Chicago'))

                # Only add if the show time is in the future
                if show_datetime_central > now:
                    next_7_days.append((show['name'], show_datetime_central))

    # Sort by datetime
    next_7_days.sort(key=lambda x: x[1])

    return next_7_days


def print_schedule(schedule):
    print("Upcoming Recordings for the Next 7 Days:\n")
    for show_name, show_datetime in schedule:
        print(f"{show_name}: {show_datetime.strftime(
            '%A, %B %d, %Y at %I:%M %p %Z')}")


if __name__ == "__main__":
    config = load_config('config.json')
    schedule = get_next_7_days_schedule(config)
    print_schedule(schedule)
