import requests
import json
import sys
import lxml.html as lh
import datetime as dt

#constants
urlBase = "https://webapp.library.uvic.ca/studyrooms/"
header={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0'}
roompref = [15,14,13,12,16,11,10,9,8]

try:
    with open('login.json') as f:
        login = json.load(f)
except:
    print("Error loading file")
    sys.exit(0)



#Scrapes the Uvic url provided and returns an array of dictionaries containing cells that are available for booking(because of the headers row and col indexing starts at 1)
def scrape(day,month,year,area):      
    page = requests.get(urlBase + "day.php?day={0}&month={1}&year={2}&area={3}".format(day,month,year,area), headers=header)
    doc = lh.fromstring(page.content)
    for T in doc.xpath('//tr'):
        if (len(T)!=10): T.getparent().remove(T)    #Uvic uses tables for other parts of the site so filter them


    tr_elements = doc.xpath('//tr')
    hr_elements = doc.xpath('//@href')


    hr_elements[:] = [tag for tag in hr_elements if "edit_entry.php?" in tag] # Filter everything that isn't an edit_entry link



    col=[]
    totalIterator = 0 #Used to get the correct entry from hr_elements
    for i in range(1, len(tr_elements)):
        j=0
        elem = tr_elements[i][0].text_content()
        holder = tr_elements[i][0].text_content().rpartition(':')[0]

        if elem[len(elem)-2] == "p" and int(holder) != 12: hour = int(holder) + 12 #Convert to 24h time
        else: hour = holder
        minute = elem.rpartition(':')[2].rpartition(' ')[0] #The 2 rpartitions are horrible but it works

        for t in tr_elements[i]: #Step through all table rows getting info
            name=t.text_content()
            
            room = hr_elements[totalIterator].split('&')[1].rpartition('=')[2] #Get room # from disgusting bunch of stuff we don't want
            if name =="\n<!--\nBeginActiveCell();\n// -->\n\n<!--\nEndActiveCell();\n// -->\n": 
                col.append(dict(hr=int(hour),min=int(minute),room=int(room),row=i,col=j,duration=30)) #Only append free rooms
                totalIterator+=1
            j+=1

    return col


#Books a slot for the given time period(String, Possible values: 30min, 1hr, 90min, 2hr). Slot is a dict of the available room
def book(slot, period):
   # url = urlBase + "edit_entry_handler.php?day={0}&month={1}&year={2}&room={3}&hour={4}&minute={5}".format(day,month,year,slot['room'],slot['hr'],slot['min'])
    url = urlBase + "edit_entry_handler.php"
    values = {'day': day,
            'month': month,
            'year': year,
            'name':'Literature Lads',
            'hour':slot['hr'],
            'minute':slot['min'],
            'duration': period,
            'netlinkid':login['username'],
            'netlinkpw':login['password'],
            'returl':'',
            'room_id':slot['room'],
            'create_by':''} #https://github.com/SavioAlp for the correct post data

    response = requests.post(url,values,headers=header)
    #print(response.content)

#Sorts a list by room #, hr, and min so they can be dealt with nicely
def sortList(list):
    return sorted(list, key=lambda k: (k['room'], k['hr'], k['min']))

#Merges back to back time slots up to 2h
def merge(list):
    i=0
    while i<len(list)-1:
        if i == len(list)-1:
            break
        elif ((list[i]['hr'] == list[i+1]['hr']) and list[i]['room'] == list[i+1]['room']): #If same hour, minute changes by 30
            if list[i]['duration'] < 120: #Max out slots at 2h
                list[i]['duration'] += 30
                list[i]['min'] = 30
                list.remove(list[i+1]) #Remove entry that was merged

        elif ((list[i]['hr'] == list[i+1]['hr'] - 1) and list[i]['room'] == list[i+1]['room']):
            if list[i]['duration'] < 120: #Max out slots at 2h
                list[i]['duration'] += 30
                list[i]['hr'] += 1
                list[i]['min'] = 0
                list.remove(list[i+1]) #Remove entry that was merged
        else:   
            i+=1
    return list

#Undo the magic done by merge()
def fixTime(list):
    toedit = [item for item in list if item['duration'] != 30]
    for item in toedit:
        if item['duration'] == 60:
            if item['min'] == 30:
                item['min'] -= 30
            else:
                item['hr'] -= 1
                item['min'] += 30

        elif item['duration'] == 90:
            item['hr'] -= 1
        
        elif item['duration'] == 120:
            item['hr'] -= 1
            if item['min'] == 30:
                item['min'] -= 30
            else:
                item['hr'] -= 1
                item['min'] += 30
                
    return list

#Convert integer durations to what uvic uses(30m,1h,90m,2h)
def convertDuration(itm):
    if itm == 30:
        return "30min"
    elif itm == 60:
        return "1hr"
    elif itm == 90:
        return "90min"
    elif itm == 120:
        return "2hr"
    else:
        return "Invalid Number"

def attemptBook(delta,startHour,startMin,endHour,endMin):
    date = dt.date.today() + dt.timedelta(days=delta) #Get however many days in the future
    year = date.year
    month = date.month
    day = date.day
    area = 1
    available = scrape(day,month,year,area)
    good = []
    for a in available: # Filter rooms by times we want
        if (startHour < int(a['hr']) < endHour):
            good.append(a)

        elif int(a['hr']) == startHour and int(a['min']) >= startMin:
            good.append(a)

        elif int(a['hr']) == endHour and int(a['min']) <= endMin:
            good.append(a)

    good = sortList(good)
    good = merge(good)
    #Now the times are the ends of the slots, fix this with fixTime
    good = fixTime(good)

    SORT_ORDER = {} #Dict to store custom room priority(eg. room 15 gets 1st priority)
    for i in range(len(roompref)):
        SORT_ORDER[str(roompref[i])] = i

    good = sorted(good, key=lambda val:(-val['duration'], SORT_ORDER.get(str(val['room'])))) #This took ages please be proud. Sorts rooms based on duration then roompref. Way overkill but some of the rooms are bad and I don't want them

    if good: 
        book(good[0],convertDuration(good[0]['duration']))
    else:
        return "No rooms found"
    return("Booked room {0} for {1} starting at {2}:{3}".format(good[0]['room'],convertDuration(good[0]['duration']),good[0]['hr'],good[0]['min']))