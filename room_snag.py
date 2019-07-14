#Run this at midnight to secure those primo rooms
import book
import datetime as dt
import sys

today = dt.date.today()
roompref = [15,14,13,12,16,11,10,9,8]

if today.weekday() == 1: #Tue
    startTime = dt.time(13,30)
    endTime = dt.time(14,30)

elif today.weekday() == 2: #Wed
    startTime = dt.time(12,30)
    endTime = dt.time(14,30)

elif today.weekday() == 3: #Thu
    startTime = dt.time(12,30)
    endTime = dt.time(14,30)
    
elif today.weekday() == 4: #Fri
    startTime = dt.time(10,30)
    endTime = dt.time(11,30)

else:
    sys.exit(0)

for i in range(1,5): # Run through all the floors
    result = book.scrapeAndBook(7,startTime,endTime,i,roompref) #Book 1 week in the future

    if result == "No rooms found":
        if i == 4: #If we're on the last floor and nothing was found
            print("Nothing Found")
        continue
    else:
        print(result)
        break
