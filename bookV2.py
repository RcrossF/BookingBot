import sys
import json
import datetime as dt
import requests
from bs4 import BeautifulSoup
import re
import datetime as dt

urlBase = "https://webapp.library.uvic.ca/studyrooms/"
header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0"
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
roomPref = [9,8,5,7,6,1,3,2,4,16,15,14,13,12,11,10]

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


# Turns the {day, month, year, area} into a url
def to_url(day, month, year, area):
    complete_url = urlBase + f"day.php?day={day}&month={month}&year={year}&area={area}"
    return complete_url

# Holds booking parameters for a cell in the bookings table
class Cell(object):
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

    # Extends a booking's duration
    def add_time(self, time):
        self.duration += time

    # Convert integer durations to what UVic uses {30m, 1h, 90m, 2h}
    def convert_duration(self):
        time_map = {30: "30min", 60: "1hr", 90: "90min", 120: "2hr"}

        try:
            return time_map[self.duration]
        except:
            if self.duration > 120:
                return time_map[120]
            else:
                return "Invalid Duration"

    # Checks if the current cell's time is between start and end
    #   eg. between (3, 30) and (5, 0) would include (3, 30), (4, 0), and (4, 30)
    def is_between_times(self, start=(0, 0), end=(0, 0)):
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


# Converts the time slot text to {hours, minutes}
def to_24_hr(time_str):
    hour = int(time_str[:-6])
    minute = int(time_str[-5:-3])
    after_12 = True if (time_str[-2:] == "pm") else False

    if after_12 and hour != 12:
        hour += 12

    return (hour, minute)


# Scrape the UVic url provided and return an array of Cell objects
def scrape(day, month, year, area):
    # IMPORTANT, DO NOT TOUCH
    # time.sleep(5)

    # Scrape the webpage for its data
    resp = requests.get(to_url(day, month, year, area))
    # Parse it with BeautifulSoup
    soup = BeautifulSoup(resp.text, "lxml")

    # Get a list of all tables and pick out the one we need
    #   Our table in interest is the fourth table
    bookings_table = soup.find("table", {'id': 'day_main'})
    bookings_table_rows = bookings_table.find_all("tr")

    existing_bookings = []
    for tr in bookings_table_rows[1:]:
        time = list(map(int, re.findall("\d{2}", tr.contents[1].text)))
        current_time = (time[0], time[1])

        #Skip all the newlines
        for td in (td for td in tr.contents[2:] if td != '\n'):
            if 'new' in td.attrs['class']:
                duration = 0
                group_name = None
                booking_id = None
                room = re.search("(?<=room=)\d", td.contents[1].contents[1].attrs['href']).group(0)
                room = int(room)

            elif 'I' in td.attrs['class']:
                #Duration can be calculated by how many cells long the booking is
                if 'rowspan' in td.attrs:
                    duration = 30*td.attrs['rowspan']
                else:
                    duration = 30
                group_name = td.contents[1].contents[1].text
                booking_id = int(td.contents[1].attrs['data-id'])
                id = "Unknown" #TODO: Find a way to get room # for already booked rooms

            area = re.search("(?<=area=)\d", td.contents[1].contents[1].attrs['href']).group(0)
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


#Flattens a multidimentional array
def flatten(something):
    if isinstance(something, (list, tuple, set, range)):
        for sub in something:
            yield from flatten(sub)
    else:
        yield something

# Search the array of cells and return all that are unbooked
def get_available(existing_bookings):
    available = []

    for cell in existing_bookings:
        if (cell.group_name is None) and (cell not in available):
            available.append(cell)

    return available


# Search the list of bookings and return those that fall between the time_slot
#   Includes start_time but does not include end_time
#   eg. between (3, 30) and (5, 0) would include (3, 30), (4, 0), and (4, 30)
def get_within_times(bookings, start_time=(0, 0), end_time=(0, 0)):
    return list(filter(lambda x: x.is_between_times(start_time, end_time), bookings))

# Filter all rooms already booked
def get_unbooked(bookings):
     return list(filter(lambda x: not x.is_booked(), bookings))

# Search the array of cells and return all that are booked by us
# TODO: Other groups that happen to use the same name as us will be matched here. Not sure how to address this yet
def get_our_bookings(existing_bookings, possible_names):
    ours = []

    for cell in existing_bookings:
        if cell.group_name in possible_names:
            ours.append(cell)

    return ours


# Sorts by the duration and room preference
def sort_by_preference(bookings):
    return sorted(bookings, key=lambda x: (-x.duration, roomPref.index(x.room_id) if roomPref.index(x.room_id) is not None else 99))

# Returns all free rooms during requested time period -offset- days in the future
def get_requested_times(offset, start_time, end_time):
    date = dt.date.today() + dt.timedelta(days=offset) #Get however many days in the future
    year = date.year
    month = date.month
    day = date.day

    rooms = []
    #Iterate through every floor except basement
    for i in [1,2]:
        rooms += scrape(day,month,year,i)

    #Filter any room not in the time we want
    unbooked_rooms = get_unbooked(rooms)
    requested_times = get_within_times(unbooked_rooms, start_time, end_time)
    good_rooms = sort_by_preference(requested_times)

    return good_rooms

get_requested_times(1, (12,0), (14,30))