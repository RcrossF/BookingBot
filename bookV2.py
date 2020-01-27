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
    "Room 113a": 1,
    "Room 113b": 2,
    "Room 113c": 3,
    "Room 113d": 4,
    "Room 131": 5,
    "Room A103": 6,
    "Room A105": 7,
    "Room A107": 8,
    "Room A109": 9,
    "Room 050a": 10,
    "Room 050b": 11,
    "Room 050c": 12,
    "Room 223": 13,
    "Room 270": 14,
    "Room 272": 15,
    "Room 274": 16
}

# Indisputable tier list of room ids
roomPref = {
    "Room A109": 0,
    "Room A107": 1,
    "Room 131": 2,
    "Room A105": 3,
    "Room A103": 4,
    "Room 113a": 5,
    "Room 113c": 6,
    "Room 113b": 7,
    "Room 113d": 8,
    "Room 274": 9,
    "Room 272": 10,
    "Room 270": 11,
    "Room 223": 12,
    "Room 050c": 13,
    "Room 050b": 14,
    "Room 050a": 15
}

# Gets the group names from an external file
try:
    with open("group_names.json") as F:
        possible_names = json.load(F)['names']
except:
    print("Error loading group_names.txt")
    sys.exit(0)

# Open the credentials file
try:
    with open("login.json") as f:
        login = json.load(f)
except:
    print("Error loading login.json")
    sys.exit(0)


def to_url(day, month, year, area):
    """ Turns the {day, month, year, area} into a url. """
    complete_url = urlBase \
        + f"day.php?day={day}&month={month}&year={year}&area={area}"
    return complete_url


class Cell(object):
    """ Holds booking parameters for a cell in the bookings table. """

    def __init__(self, room_name, group_name, booking_id,
                 area, day, time, duration):
        self.room_name = room_name
        self.room_id = room_ids[room_name]
        self.group_name = group_name
        self.booking_id = booking_id
        self.area = area
        self.day = day
        # Time in seconds
        self.time = time
        # Available duration in seconds
        self.duration = duration

    def is_booked(self):
        return (self.booking_id is not None)

    def is_between_times(self, start=0, end=0):
        """
        Checks if the current cell's time is between 'start' and 'end'.

        eg. Between 12600 and 18000 would include 12600 <= x < 18000.
        """

        return start <= self.time and self.time < end

    def __repr__(self):
        return (f"{self.group_name} has "
                f"{self.room_name} at "
                f"{self.time} for "
                f"{self.duration} seconds.")


def scrape(day, month, year, area):
    # TODO Find a way to get room names
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

    # Get the room names from the header
    booking_table_header = bookings_table_rows[0].find_all("th")
    room_names = [x.text.strip()[:-3] for x in booking_table_header]

    existing_bookings = []
    for tr in bookings_table_rows[1:]:
        # Gets the time, in seconds, of the row
        row_time = int(tr.find("td", attrs={"class": "row_labels"})[
                       "data-seconds"])

        row_cols = tr.find_all("td")
        for i in range(1, len(row_cols)):
            """
            In each <td> tag:
            - td_class tells you if the room is booked or unbooked.
            - <a> tags contain the group name or nothing if unbooked.
            - link in the <a> tag contains the date.
            - div_class tells you the duration and booking id.
            """
            raw_cell = row_cols[i]

            # Room unbooked
            if raw_cell.attrs["class"] == ["new"]:
                duration = 1800
                group_name = None
                booking_id = None
                # room = room_names[i]

            elif raw_cell.attrs["class"] == ["I"]:
                raw_cell_div = raw_cell.find("div").attrs
                duration = int(raw_cell_div["class"][-1][-1]) * 1800
                group_name = raw_cell.text.strip()
                booking_id = int(raw_cell_div["data-id"])

            else:
                raise ValueError("Unexpected cell")

            existing_bookings.append(
                Cell(
                    None,
                    group_name,
                    booking_id,
                    area,
                    day,
                    row_time,
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


def get_within_times(bookings, start=0, end=0):
    """
    Return bookings that are within the given times.

    eg. Between 12600 and 18000 would include 12600 <= x < 18000.
    """
    return list(filter(lambda x: x.is_between_times(start, end), bookings))


def get_unbooked(bookings):
    """ Filter all rooms already booked. """
    return list(filter(lambda x: not x.is_booked(), bookings))


def get_our_bookings(existing_bookings, possible_names):
    """
    Search the array of cells and return all that are booked by us

    TODO: Other groups that happen to use the same name
    as us will be matched here. Not sure how to address this yet
    """
    ours = []

    for cell in existing_bookings:
        if cell.group_name in possible_names:
            ours.append(cell)

    return ours


def sort_by_preference(bookings):
    """ Sorts by the duration and room preference. """
    return sorted(bookings, key=lambda x: (-x.duration, roomPref[x.room_name]))


def get_requested_times(offset, start_time, end_time):
    """
    Return all free rooms during requested time period,
    'offset' days in the future.
    """
    # Get however many days in the future
    date = dt.date.today() + dt.timedelta(days=offset)
    year = date.year
    month = date.month
    day = date.day

    rooms = []
    # Iterate through every floor except basement
    for i in [1, 3]:
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

    # Merge adjacent cells, assumes all cells have a 30min duration
    i = len(good_rooms) - 1
    while i > 1:
        prev_h = good_rooms[i-1].time[0]
        prev_m = good_rooms[i-1].time[1]
        cur_h = good_rooms[i].time[0]
        cur_m = good_rooms[i].time[1]

        if good_rooms[i-1].room_id == good_rooms[i].room_id:
            if (prev_h == cur_h or (abs(prev_h - cur_h) == 1 and prev_m == 30 and cur_m == 0)) and good_rooms[i-1].duration < 120:
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
            start_seconds = cell.time
            end_seconds = start_seconds + cell.duration
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
make_booking(get_requested_times(offset, 43200, 52200), offset)
