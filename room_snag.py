'''
Run this after the library closes for the day. Rooms are booked 1 week in advance
'''
from bookV2 import book
import datetime as dt
import sys
import json
import pytz

target_day = dt.datetime.now(pytz.timezone('US/Pacific')).date()
weekday = target_day.strftime('%A')

try:
    with open("snag_times.json") as f:
        booking_times = json.load(f)[weekday]
except:
    print(f"Error loading snag_times.json")
    sys.exit(0)

for times in booking_times:
    # This supports multiple non-continuous booking slots
    start_str = times['bookingStart']
    end_str = times['bookingEnd']

    start_h, start_m = map(int, start_str.split(':'))
    end_h, end_m = map(int, end_str.split(':'))

    start = dt.timedelta(hours=start_h, minutes=start_m)
    end = dt.timedelta(hours=end_h, minutes=end_m)

    for i in range(1,4): # Run through all the floors
        result = book(7, start.total_seconds(), end.total_seconds())
        if result == "No rooms found":
            if i == 3: #If we're on the last floor and nothing was found
                print(f"Nothing found from {start_str}-{end_str}")
            continue
        else:
            break
