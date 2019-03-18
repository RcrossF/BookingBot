import requests
import lxml.html as lh
from lxml import etree
import datetime

year = 2019
month = 3
day = 20
area = 1
urlBase = "https://webapp.library.uvic.ca/studyrooms/"
startHour = 11
startMin = 30
endHour = 13
endMin = 30

#print(url + "day={0}&month={1}&year={2}&area={3}".format(day,month,year,area))



#Scrapes the Uvic url provided and returns an array of dictionaries containing cells that are available for booking(because of the headers row and col indexing starts at 1)
def scrape():      
    page = requests.get(urlBase + "day.php?day={0}&month={1}&year={2}&area={3}".format(day,month,year,area))
    doc = lh.fromstring(page.content)
    for T in doc.xpath('//tr'):
        if (len(T)!=10): T.getparent().remove(T)    #Uvic uses tables for other parts of the site so filter them


    tr_elements = doc.xpath('//tr')
    hr_elements = doc.xpath('//@href')


    hr_elements[:] = [tag for tag in hr_elements if "edit_entry.php?" in tag] # Filter everything that isn't an edit_entry link

    for tag in hr_elements:
        if "edit_entry.php?" in tag:    print(tag)
        


    col=[]
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
            
            room = "a"
            if name =="\n<!--\nBeginActiveCell();\n// -->\n\n<!--\nEndActiveCell();\n// -->\n": col.append(dict(hr=hour,min=minute,room=room,row=i,col=j)) #Only append free rooms
            j+=1
                    
    return col


def book(good):
    url = urlBase + "edit_entry.php?day={0}&month={1}&year={2}&room={3]".format(day,month,year,room)

available = scrape()
good = []
for a in available:
     if (startHour < int(a['hr']) < endHour):
         good.append(a)

     elif int(a['hr']) == startHour and int(a['min']) >= startMin:
         good.append(a)

     elif int(a['hr']) == endHour and int(a['min']) <= endMin:
        good.append(a)

#print(good)