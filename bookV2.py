import sys
import json
import datetime as dt
import requests
from bs4 import BeautifulSoup
import re
import base64
from numpy import random
from enum import Enum

from utils import flatten, get_available, get_within_times, get_our_bookings, get_unbooked, sort_by_prefrence, to_uvic_url

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

class Floors(Enum):
    BASEMENT = 0
    FIRST = 1
    SECOND = 2

@dataclass
class Room:
    """
    Represents a bookable room. Quality ranges from 0 to 10
    """
    quality: int
    floor: Floors
    name: str
    id: int

@dataclass
class Rooms(Enum):
    ROOM113A = Room(quality=5, floor=Floors.FIRST, name='Room 113a', id=1)
    ROOM113B = Room(quality=4, floor=Floors.FIRST, name='Room 113b', id=2)
    ROOM113C = Room(quality=3, floor=Floors.FIRST, name='Room 113c', id=3)
    ROOM113D = Room(quality=8, floor=Floors.FIRST, name='Room 113c', id=4)
    ROOM131 = Room(quality=8, floor=Floors.FIRST, name='Room 131', id=5)
    ROOMA103 = Room(quality=6, floor=Floors.FIRST, name='Room A103', id=6)
    ROOMA105 = Room(quality=7, floor=Floors.FIRST, name='Room A105', id=7)
    ROOMA107 = Room(quality=9, floor=Floors.FIRST, name='Room A107', id=8)
    ROOMA109 = Room(quality=10, floor=Floors.FIRST, name='Room A109', id=9)
    ROOM050A = Room(quality=1, floor=Floors.BASEMENT, name='Room 050A', id=10)
    ROOM050B = Room(quality=1, floor=Floors.BASEMENT, name='Room 050B', id=11)
    ROOM050C = Room(quality=1, floor=Floors.BASEMENT, name='Room 050C', id=12)
    ROOM223 = Room(quality=2, floor=Floors.SECOND, name='Room 223', id=13)
    ROOM270 = Room(quality=2, floor=Floors.SECOND, name='Room 270', id=14)
    ROOM272 = Room(quality=2, floor=Floors.SECOND, name='Room 272', id=15)
    ROOM274 = Room(quality=2, floor=Floors.SECOND, name='Room 274', id=16)


def load_credentials():
    """
    Loads uvic credentials and ground names from disk
    """
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
