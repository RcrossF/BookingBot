#Run this at midnight to secure those primo rooms
from bookV2 import book
import datetime as dt
import sys

today = dt.date.today()

# if today.weekday() == 1: #Tue
#     startTime = dt.time(13,30)
#     endTime = dt.time(14,30)

# elif today.weekday() == 2: #Wed
#     startTime = dt.time(12,30)
#     endTime = dt.time(14,30)

# elif today.weekday() == 3: #Thu
#     startTime = dt.time(12,30)
#     endTime = dt.time(14,30)
    
# elif today.weekday() == 4: #Fri
#     startTime = dt.time(10,30)
#     endTime = dt.time(11,30)

# else:
#     sys.exit(0)
startTime = dt.timedelta(hours=15, minutes=0)
endTime = dt.timedelta(hours=15, minutes=30)


for i in range(1,4): # Run through all the floors
    result = book(6, startTime.total_seconds(), endTime.total_seconds())
    if result == "No rooms found":
        if i == 3: #If we're on the last floor and nothing was found
            print("Nothing Found")
        continue
    else:
        print(result+"\n")
        break
