#Run this at midnight to secure those primo rooms
import book
import datetime as dt
import sys

today = dt.date.today()
roompref = [15,14,13,12,16,11,10,9,8]

if today.weekday() == 2: #Wed
    startTime = dt.time(11,30)
    endTime = dt.time(13,30)

elif today.weekday() == 3: #Thu
    startTime = dt.time(13,0)
    endTime = dt.time(14,30)

elif today.weekday() == 4: #Fri
    startTime = dt.time(11,30)
    endTime = dt.time(13,30)

else:
    sys.exit(0)

for i in range(1,5): # Run through all the floors but 4, it breaks everything because it is missing a href tag somewhere
    result = book.scrapeAndBook(7,startTime,endTime,i,roompref)

    if result == "No rooms found":
        if i == 4: #If we're on the last floor and nothing was found
            print("Nothing Found")
        continue
    else:
        print(result)
        break
