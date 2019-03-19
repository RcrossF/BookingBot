import requests
import json
import sys
import lxml.html as lh
from lxml import etree
from datetime import datetime as dt

year = dt.now().year
month = dt.now().month
day = dt.now().day + 1
area = 1
urlBase = "https://webapp.library.uvic.ca/studyrooms/"
header={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0'}
startHour = 11
startMin = 30
endHour = 13
endMin = 30
roompref = []
try:
    login = json.load("/login.json")
except:
    print("Error loading file")
    sys.exit()
#Scrapes the Uvic url provided and returns an array of dictionaries containing cells that are available for booking(because of the headers row and col indexing starts at 1)
def scrape():      
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

        #if time[len(time)-2] == "a": hour = holder
        if elem[len(elem)-2] == "p" and int(holder) != 12: hour = int(holder) + 12 #Convert to 24h time
        else: hour = holder
        minute = elem.rpartition(':')[2].rpartition(' ')[0] #I know the 2 rpartitions are horrible but it works

        for t in tr_elements[i]:
            name=t.text_content()
            
            room = hr_elements[totalIterator].split('&')[1].rpartition('=')[2] #Get room # from disgusting bunch of stuff we don't want
            if name =="\n<!--\nBeginActiveCell();\n// -->\n\n<!--\nEndActiveCell();\n// -->\n": 
                col.append(dict(hr=hour,min=minute,room=room,row=i,col=j)) #Only append free rooms
                totalIterator+=1
            j+=1
            
                    
    return col


#Books a slot for the given time(String. Possible values: 30min, 1hr, 90min, 2hr), good luck testing this before uvic rate limits you
def book(slot, period):
   # url = urlBase + "edit_entry_handler.php?day={0}&month={1}&year={2}&room={3}&hour={4}&minute={5}".format(day,month,year,slot['room'],slot['hr'],slot['min'])
    url = urlBase + "edit_entry_handler.php"
    values = {'day': day,
            'month': month,
            'year': year,
            'name':'StudyBois',
            'hour':slot['hr'],
            'minute':slot['min'],
            'duration': period,
            'netlinkid':login['username'],
            'netlinkpw':login['password'],
            'returl':'',
            'room_id':slot['room'],
            'create_by':''} #https://github.com/SavioAlp for the correct post data

    response = requests.post(url,values,headers=header)
    print(response.content)


available = scrape()
good = []
for a in available: # Filter rooms by times we want
     if (startHour < int(a['hr']) < endHour):
         good.append(a)

     elif int(a['hr']) == startHour and int(a['min']) >= startMin:
         good.append(a)

     elif int(a['hr']) == endHour and int(a['min']) <= endMin:
        good.append(a)
        
#print(good)


book(good[0],"30min")