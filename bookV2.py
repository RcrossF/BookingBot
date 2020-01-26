import sys
import json
import datetime as dt
import requests
from bs4 import BeautifulSoup
import re
import base64
from numpy import random

loginUrl = "https://www.uvic.ca/cas/login"
urlBase = "https://webapp.library.uvic.ca/studyrooms/"
header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0",
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip',
    'DNT': '1',
    'Connection': 'close'
}

room_ids = {
    1: "Room 113a",
    2: "Room 113b",
    3: "Room 113c",
    4: "Room 113d",
    5: "Room 131",
    6: "Room A103",
    7: "Room A105",
    8: "Room A107",
    9: "Room A109",
    10: "Room 050a",
    11: "Room 050b",
    12: "Room 050c",
    13: "Room 223",
    14: "Room 270",
    15: "Room 272",
    16: "Room 274"
}

# Indisputable tier list of room ids
roomPref = [9, 8, 5, 7, 6, 1, 3, 2, 4, 16, 15, 14, 13, 12, 11, 10]

# Gets the group names from an external file
try:
    with open("group_names.json") as F:
        possible_names = json.load(F)['names']
except:
    print("Error loading group_names.txt")
    sys.exit(0)

# Open the credentials file
# try:
#     with open("login.json") as f:
#         login = json.load(f)
# except:
#     print("Error loading login.json")
#     sys.exit(0)


def to_url(day, month, year, area):
    """ Turns the {day, month, year, area} into a url. """
    complete_url = urlBase + \
        f"day.php?day={day}&month={month}&year={year}&area={area}"
    return complete_url


class Cell(object):
    """ Holds booking parameters for a cell in the bookings table. """

    def __init__(
        self,
        room_id,
        group_name,
        booking_id,
        area,
        day,
        time,
        duration
    ):
        self.room_name = room_ids[room_id]
        self.room_id = room_id
        self.group_name = group_name
        self.booking_id = booking_id
        self.area = area
        self.day = day
        # Time in (hours, minutes)
        self.time = time
        # Available duration in minutes
        self.duration = duration

    def is_booked(self):
        return (self.booking_id is not None)

    def add_time(self, time):
        """ Extends a booking's duration. """
        self.duration += time

    def convert_duration(self):
        """ Convert integer durations to what UVic uses {30m, 1h, 90m, 2h}. """
        time_map = {30: "30min", 60: "1hr", 90: "90min", 120: "2hr"}

        try:
            return time_map[self.duration]
        except:
            if self.duration > 120:
                return time_map[120]
            else:
                return "Invalid Duration"

    def is_between_times(self, start=(0, 0), end=(0, 0)):
        """
        Checks if the current cell's time is between 'start' and 'end'.
        eg. between (3, 30) and (5, 0) would include (3, 30), (4, 0), and (4, 30)
        """
        lower_bound = start[1] + 60 * start[0]
        upper_bound = end[1] + 60 * end[0]
        my_time = self.time[1] + 60 * self.time[0]

        return lower_bound <= my_time and my_time < upper_bound

    def print_cell(self):
        if self.is_booked:
            print(
                f"At {self.time[0]}:{self.time[1]}, {self.group_name} booked {self.room_name} for {self.duration} minutes."
            )

        else:
            print(
                f"At {self.time[0]}:{self.time[1]}, {self.room_name} is available for {self.duration} minutes."
            )

    def __repr__(self):
        return f"{self.room_name} at {self.time[0]:02}:{self.time[1]:02} for {self.duration} minutes."


def to_24_hr(time_str):
    """ Converts the time slot text to {hours, minutes}. """
    hour = int(time_str[:-6])
    minute = int(time_str[-5:-3])
    after_12 = True if (time_str[-2:] == "pm") else False

    if after_12 and hour != 12:
        hour += 12

    return (hour, minute)


def scrape(day, month, year, area):
    """ Scrape the given date and area and return an array of Cell objects. """
    # IMPORTANT, DO NOT TOUCH
    # time.sleep(5)

    # Scrape the webpage for its data
    resp = requests.get(to_url(day, month, year, area), headers=header)
    # Parse it with BeautifulSoup
    soup = BeautifulSoup(resp.text, "lxml")

    # Get a list of all tables and pick out the one we need
    #   Our table in interest is the fourth table
    bookings_table = soup.find("table", {'id': 'day_main'})
    bookings_table_rows = bookings_table.find_all("tr")

    existing_bookings = []
    for tr in bookings_table_rows[1:]:
        time = list(map(int, re.findall("\d{2}", tr.contents[1].text)))

        # Account for 24h time
        if "PM" in tr.contents[1].text and time[0] != 12:
            time[0] += 12
        current_time = (time[0], time[1])

        # Skip all the newlines
        for td in (td for td in tr.contents[2:] if td != '\n'):
            if 'new' in td.attrs['class']:
                duration = 30
                group_name = None
                booking_id = None
                room = re.search(
                    "(?<=room=)\d", td.contents[1].contents[1].attrs['href']).group(0)
                room = int(room)

            elif 'I' in td.attrs['class']:
                # Duration can be calculated by how many cells long the booking is
                if 'rowspan' in td.attrs:
                    duration = 30*td.attrs['rowspan']
                else:
                    duration = 30
                group_name = td.contents[1].contents[1].text
                booking_id = int(td.contents[1].attrs['data-id'])
                id = "Unknown"  # TODO: Find a way to get room # for already booked rooms

            area = re.search(
                "(?<=area=)\d", td.contents[1].contents[1].attrs['href']).group(0)
            area = int(area)

            existing_bookings.append(
                Cell(
                    room,
                    group_name,
                    booking_id,
                    area,
                    day,
                    current_time,
                    duration
                )
            )

    return existing_bookings


def flatten(something):
    """ Flattens a multidimensional array. """
    if isinstance(something, (list, tuple, set, range)):
        for sub in something:
            yield from flatten(sub)
    else:
        yield something


def get_available(existing_bookings):
    """ Search the array of cells and return all that are unbooked. """
    available = []

    for cell in existing_bookings:
        if (cell.group_name is None) and (cell not in available):
            available.append(cell)

    return available


def get_within_times(bookings, start_time=(0, 0), end_time=(0, 0)):
    """
    Search the list of bookings and return those that fall between the time_slot

    Includes start_time but does not include end_time

    eg. between (3, 30) and (5, 0) would include (3, 30), (4, 0), and (4, 30)
    """
    return list(filter(lambda x: x.is_between_times(start_time, end_time), bookings))


def get_unbooked(bookings):
    """ Filter all rooms already booked. """
    return list(filter(lambda x: not x.is_booked(), bookings))


def get_our_bookings(existing_bookings, possible_names):
    """
    Search the array of cells and return all that are booked by us

    TODO: Other groups that happen to use the same name as us will be matched here. Not sure how to address this yet
    """
    ours = []

    for cell in existing_bookings:
        if cell.group_name in possible_names:
            ours.append(cell)

    return ours


def sort_by_preference(bookings):
    """ Sorts by the duration and room preference. """
    return sorted(bookings, key=lambda x: (-x.duration, roomPref.index(x.room_id)))


def get_requested_times(offset, start_time, end_time):
    """
    Return all free rooms during requested time period, 'offset' days in the future.
    """
    # Get however many days in the future
    date = dt.date.today() + dt.timedelta(days=offset)
    year = date.year
    month = date.month
    day = date.day

    rooms = []
    # Iterate through every floor except basement
    for i in [1, 2]:
        rooms += scrape(day, month, year, i)

    # Filter any room not in the time we want
    unbooked_rooms = get_unbooked(rooms)
    requested_times = get_within_times(unbooked_rooms, start_time, end_time)
    good_rooms = sort_by_preference(requested_times)

    # Drop duplicate times
    times = []
    i = 0
    while i < len(good_rooms):
        if good_rooms[i].time not in times:
            times.append(good_rooms[i].time)
            i += 1
        else:
            del(good_rooms[i])

    # Merge adjacent cells, assumes all cells have a 30min duration at this point
    i = len(good_rooms) - 1
    while i > 1:
        prev_h = good_rooms[i-1].time[0]
        prev_m = good_rooms[i-1].time[1]
        cur_h = good_rooms[i].time[0]
        cur_m = good_rooms[i].time[1]

        if good_rooms[i-1].room_id == good_rooms[i].room_id:
            if (prev_h == cur_h or (abs(prev_h - cur_h) == 1
                                    and prev_m == 30 and cur_m == 0)) and good_rooms[i-1].duration < 120:
                good_rooms[i-1].duration += good_rooms[i].duration
                del(good_rooms[i])
                i = len(good_rooms) - 1
                continue

        i -= 1

    return good_rooms


def make_booking(cells, offset):
    """
    Tries to make a booking for each cell, 'offset' days in the future.
    """
    # Get however many days in the future
    date = dt.date.today() + dt.timedelta(days=offset)
    date_str = date.strftime("%Y-%m-%d")

    for cell in cells:
        for user in login['users']:
            # Create a new session
            s = requests.Session()

            # Get the execution token from login page
            resp = s.get(
                loginUrl+"?service=https://webapp.library.uvic.ca/studyrooms/edit_entry.php", headers=header)
            # Parse it with BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            execution_token = soup.find(
                attrs={"name": "execution"}).attrs['value']

            # Log in
            password = str(base64.standard_b64decode(user['password']))
            # Remove extra base64 decode characters
            password = password[2:-1]
            params = {
                "username": user['username'],
                "password": password,
                "execution": execution_token,
                "_eventId": "submit"
            }
            s.post(loginUrl, params, headers=header)

            # See if login was successful
            resp = s.get(urlBase+"edit_entry.php", headers=header)
            # Parse it with BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            if "Please login to create" in soup:
                print("Login for user "+user+" failed")
                continue  # Login failed, move to next account

            # Get CSRF token
            csrf_token = soup.find(
                attrs={"name": "csrf_token"}).attrs['content']

            # Uvic now uses seconds as the booking time. Go figure...
            start_seconds = cell.time[0] * 3600 + cell.time[1] * 60
            end_seconds = start_seconds + cell.duration * 60
            params = {
                "csrf_token": csrf_token,
                "create_by": "",
                "rep_id": 0,
                "edit_type": "series",
                "name": random.choice(possible_names),
                "rooms[]": cell.room_id,
                "start_date": date_str,
                "end_date": date_str,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds
            }

            # Make the final booking request
            resp = s.post(urlBase+"edit_entry.php", headers=header)

            # Account maxed, move onto next
            if "The maximum number of bookings" in resp.text:
                continue

            # Sucessful booking, break out of user loop
            cell.print_cell()
            break


offset = 1
# make_booking(get_requested_times(offset, (12, 0), (14, 30)), offset)
for r in get_requested_times(offset, (12, 0), (14, 30)):
    print(r)
