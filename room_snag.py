#Run this at midnight to secure those primo rooms
import book
import datetime as dt
import sys

today = dt.date.today()
roompref = [15,14,13,12,16,11,10,9,8]

if today.weekday() == 2: #Wed
    startHour = 11
    startMin = 30
    endHour = 13
    endMin = 30

elif today.weekday() == 3: #Thu
    startHour = 13
    startMin = 0
    endHour = 14
    endMin = 30

elif today.weekday() == 4: #Fri
    startHour = 11
    startMin = 30
    endHour = 13
    endMin = 30

else:
    sys.exit(0)

for i in range(1,5): # Run through all the floors but 4, it breaks everything because it is missing a href tag somewhere
    result = book.scrapeAndBook(7,startHour,startMin,endHour,endMin,i,roompref)

    if result == "No rooms found":
        if i == 4: #If we're on the last floor and nothing was found
            print("Nothing Found")
        continue
    else:
        print(result)
        break
    