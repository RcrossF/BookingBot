import sys
import json
import datetime as dt
import requests
from bs4 import BeautifulSoup
import re
import base64
from numpy import random
from enum import Enum
from dataclasses import dataclass
import pytz
from math import modf

from utils import flatten, get_available, get_within_times, get_our_bookings, get_unbooked, sort_by_prefrence, to_uvic_url

loginUrl = "https://www.uvic.ca/cas/login"
urlBase = "https://webapp.library.uvic.ca/studyrooms/"
header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded'
}

class Floors(Enum):
    BASEMENT = 0
    FIRST = 1
    SECOND = 2

@dataclass
class Room:
    """
    Represents a bookable room. Quality ranges from 0 to 10. Quality does not have to be unique
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
    ROOM113D = Room(quality=8, floor=Floors.FIRST, name='Room 113d', id=4)
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

room_map = {
    1: Rooms.ROOM113A,
    2: Rooms.ROOM113B,
    3: Rooms.ROOM113C,
    4: Rooms.ROOM113D,
    5: Rooms.ROOM131,
    6: Rooms.ROOMA103,
    7: Rooms.ROOMA105,
    8: Rooms.ROOMA107,
    9: Rooms.ROOMA109,
    10: Rooms.ROOM050A,
    11: Rooms.ROOM050B,
    12: Rooms.ROOM050C,
    13: Rooms.ROOM223,
    14: Rooms.ROOM270,
    15: Rooms.ROOM272,
    16: Rooms.ROOM274
}

class Credentials():
    login = None
    group_names = None

    def __init__(self, cred_file, group_names_file):
        self.login, self.group_names = self.load_credentials(cred_file, group_names_file)

    def load_credentials(self, cred_file, group_names_file):
        """
        Loads uvic credentials and ground names from disk
        """
        try:
            with open(group_names_file) as F:
                possible_names = json.load(F)['names']
        except:
            print(f"Error loading {group_names_file}")
            sys.exit(0)

        # Open the credentials file
        try:
            with open(cred_file) as f:
                login = json.load(f)
        except:
            print(f"Error loading {cred_file}")
            sys.exit(0)

        return login, possible_names

class Cell(object):
    """ Holds booking parameters for a cell in the bookings table. """

    def __init__(self, room, group_name, booking_id,
                 area, day, time, duration):
        self.room_meta = room # Room object
        self.group_name = group_name
        self.booking_id = booking_id
        self.area = area
        self.day = day
        # Time in seconds since 12am. 
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

    # TODO: Make these nicer with hours and proper times
    def __repr__(self):
        if self.booking_id is not None:
            return (f"{self.group_name} has "
                    f"{self.room_meta.name} at "
                    f"{self.time} for "
                    f"{self.duration} seconds.")
        else:
            human_time = dt.timedelta(seconds=self.time)
            hour = human_time.seconds // 3600
            minute = (human_time.seconds//60) % 60
            return f"{self.room_meta.name} is unbooked at {hour}:{minute} for {self.duration / 3600} hours." 


def scrape(day, month, year, area):
    # TODO Find a way to get room names
    """ Scrape the given date and area and return an array of Cell objects. """
    # IMPORTANT, DO NOT TOUCH
    # time.sleep(5)

    # Scrape the webpage for its data
    resp = requests.get(to_uvic_url(day, month, year, area), headers=header, verify=False) # TODO: Fix ssl error
    # Parse it with BeautifulSoup
    soup = BeautifulSoup(resp.text, "lxml")

    # Get a list of all tables and pick out the one we need
    bookings_table = soup.find("table", {'id': 'day_main'})
    bookings_table_rows = bookings_table.find_all("tr")

    # Get the room ids from the header
    booking_table_header = bookings_table_rows[0].find_all("th")
    room_ids = [int(x['data-room']) for x in booking_table_header[1:]]

    existing_bookings = []
    for tr in bookings_table_rows[1:]:
        # Gets the time of the row. Format is seconds since midnight
        row_time = int(tr.find("th")[
                       "data-seconds"])


        row_cols = tr.find_all("td")
        for raw_cell, room_id in zip(row_cols, room_ids):
            """
            In each <td> tag:
            - td_class tells you if the room is booked or unbooked.
            - <a> tags contain the group name or nothing if unbooked.
            - link in the <a> tag contains the date.
            - div_class tells you the duration and booking id.
            """
            duration = 1800 # Default booking is 30 minutes
            if 'rowspan' in raw_cell.attrs:
                duration = int(raw_cell.attrs["rowspan"]) * 1800

            # Room unbooked
            if "new" in raw_cell.attrs["class"]:
                # Room id can be affected by rowspan so update it here
                room_id = int(re.search(r'(?<=room\=)\d', raw_cell.find('a').attrs['href']).group())
                group_name = None
                booking_id = None
                
            
            # TODO: Booked rooms can take the wrong room ID with the current method. Find something better.
            # This is not needed for room booking but would be nice for additional functionality
            elif "booked" in raw_cell.attrs["class"]:
                continue
                group_name = raw_cell.text.strip()
                raw_cell_div = raw_cell.find("div")
                booking_id = int(raw_cell_div.find('a').attrs["data-id"])

            else:
                raise ValueError("Unexpected cell")

            room = room_map[room_id].value
            
            existing_bookings.append(
                Cell(
                    room,
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
    # Get however many days in the future. UVIC is in PST so force this timezone
    date = dt.datetime.now(pytz.timezone('US/Pacific')).date() + dt.timedelta(days=offset)
    year = date.year
    month = date.month
    day = date.day

    rooms = []
    # Iterate through every floor except the basement (yuck)
    for i in [1, 3]:
        rooms += scrape(day, month, year, i)

    # Filter any room not in the time we want
    unbooked_rooms = get_unbooked(rooms)
    requested_times = get_within_times(unbooked_rooms, start_time, end_time)
    good_rooms = sort_by_prefrence(requested_times)

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
    while i >= 1:
        prev_h = int(good_rooms[i-1].time / 3600)
        prev_m = int(modf((good_rooms[i-1].time / 3600))[0] * 60)
        cur_h = int(good_rooms[i].time / 3600)
        cur_m = int(modf((good_rooms[i].time / 3600))[0] * 60)

        if good_rooms[i-1].room_meta.id == good_rooms[i].room_meta.id:
            if (prev_h == cur_h or (abs(prev_h - cur_h) == 1 and prev_m == 30 and cur_m == 0)) and good_rooms[i-1].duration < 7200:
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
    if len(cells) == 0:
        return "No rooms found"
        
    # Get however many days in the future
    date = dt.date.today() + dt.timedelta(days=offset)
    date_str = date.strftime("%Y-%m-%d")

    print(f"Booking for {date_str}")

    creds = Credentials('login.json', 'group_names.json')
    users = creds.login['users']
    for cell in cells:
        for user in users:
            # Create a new session
            with requests.Session() as s:

                # Get the execution token from login page
                resp = s.get(
                    loginUrl+f"?service=https://webapp.library.uvic.ca/studyrooms/edit_entry.php", headers=header)
                # Parse it with BeautifulSoup
                soup = BeautifulSoup(resp.text, "lxml")
                execution_token = soup.find(
                    attrs={"name": "execution"}).attrs['value']

                # Log in
                password = str(base64.standard_b64decode(user['password']))
                # Remove extra base64 decode characters
                password = password[2:-1]
                login_params = {
                    "username": user['username'],
                    "password": password,
                    "execution": execution_token,
                    "rememberMe": True,
                    "_eventId": "submit"
                }
                lg = s.post(loginUrl+f"?service=https://webapp.library.uvic.ca/studyrooms/edit_entry.php?year={date.year}&month={date.month}&day={date.day}&area={cell.area}&room={cell.room_meta.id}", login_params, headers=header, verify=False)
                #s.post(loginUrl+"?service=https://webapp.library.uvic.ca/studyrooms/edit_entry_handler.php", params, headers=header, verify=False)
                #See if login was successful
                resp = s.get(f"https://webapp.library.uvic.ca/studyrooms/edit_entry.php?year={date.year}&month={date.month}&day={date.day}&area={cell.area}", headers=header, verify=False)
    
                if "Please login to create" in resp.text:
                   print(f"Login for user {user} failed")
                   continue  # Login failed, move to next account

                #Parse it with BeautifulSoup
                soup = BeautifulSoup(resp.text, "lxml")
                # Get CSRF token
                csrf_token = soup.find(
                    attrs={"name": "csrf_token"}).attrs['content']

                # Uvic now uses seconds as the booking time. Go figure...
                start_seconds = cell.time
                end_seconds = start_seconds + cell.duration
                params = {
                    "csrf_token": csrf_token,
                    'returl': f"https://webapp.library.uvic.ca/studyrooms/index.php?year={date.year}&month={date.month}&day={date.day}&area={cell.area}",
                    'create_by': user['username'],
                    "rep_id": 0,
                    "edit_type": "series",
                    "name": random.choice(creds.group_names),
                    "rooms[]": cell.room_meta.id,
                    "start_date": date_str,
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds
                }

                # Make the final booking request
                resp = s.post(urlBase+"edit_entry_handler.php", params, headers=header, verify=False, allow_redirects=False)

                if "Please login" in resp.text:
                    raise ConnectionError("Signed out, something is probably wrong with the booking request")

                # Account maxed, move onto next
                if "The maximum number of bookings" in resp.text:
                    continue

                # Sucessful booking, break out of user loop
                print(cell)
                break

def book(days_in_future, start_time, end_time):
    """
    Helper function to make booking a lil easier.
    Params:
    (int) days in future to book
    (int) Start time of desired booking, in seconds since midnight (i know this is stupid)
    (int) End time of desired booking, in seconds since midnight
    """
    return make_booking(get_requested_times(days_in_future, start_time, end_time), days_in_future)
