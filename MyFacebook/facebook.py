import atexit
import json
import re
import networkx as nx
import os
import matplotlib.pyplot as plt
import hashlib
import time
import csv
import sqlite3

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import *

#______________________________________________________________________________
# go to the end of page to load it completely
def loadPageCompletely(addr):
    print("Loading: " + addr)
    driver.get(addr)
    ps1 = ""
    ps2 = driver.page_source
    body = driver.find_element_by_xpath('/html/body')
    while ps1 != ps2:
        print(".", end=' ')
        time.sleep(5)
        #.send_keys(Keys.CONTROL+Keys.END)
        body.send_keys(Keys.END)
        ps1 = ps2
        ps2 = driver.page_source
    print()
    
#______________________________________________________________________________
def getMainUserFriendsListAddress():
    profileLink = driver.find_element_by_class_name("_2s25")
    driver.get(profileLink.get_attribute("href"))

    tabs = driver.find_elements_by_class_name("_6-6")
    for tab in tabs:
        if tab.get_attribute("data-tab-key") == "friends":
            return tab.get_attribute("href")
            break
#______________________________________________________________________________
def getUserName():
    element = driver.find_element_by_id("fb-timeline-cover-name")
    return element.text
#______________________________________________________________________________
def createDatabase():
    db = sqlite3.connect('facebook.db')
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT,
            url TEXT, 
            level INTEGER,
            touched BOOLEAN DEFAULT 0,
            UNIQUE (name) ON CONFLICT IGNORE)
    ''')
    db.commit()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges(
            source INTEGER,
            target INTEGER, 
            PRIMARY KEY (source, target) ON CONFLICT IGNORE)
    ''')
    db.commit()
    return db
#______________________________________________________________________________
def insertNode(db, name, url, level):
    print("......... "+name)
    cursor = db.cursor()
    cursor.execute('''INSERT INTO nodes(name, url, level)
                VALUES(?,?,?)''', (name, url, level))
    db.commit()
    return cursor.lastrowid
#______________________________________________________________________________
def insertEdge(db, source, dest):
    cursor = db.cursor()
    cursor.execute('''INSERT INTO edges(source, target)
                VALUES(?,?)''', (source, dest))
    db.commit()
    
def clearDatabase():
    cursor = db.cursor()
    cursor.execute('''DELETE FROM nodes''')
    cursor.execute('''DELETE FROM edges''')
    db.commit()
    
#______________________________________________________________________________
def setTouched(currentUserId):
    cursor = db.cursor()
    cursor.execute('''UPDATE nodes SET touched=1 WHERE id='''+ str(currentUserId))
    db.commit()
    print("Done: "+ str(currentUserId))
    
#______________________________________________________________________________
def getUntouchedRow():
    cursor = db.cursor()
    cursor.execute('SELECT * FROM nodes WHERE touched=0 ORDER BY id')
    return cursor.fetchone()

#______________________________________________________________________________
def hasUntouchedRow():
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) FROM nodes WHERE touched=0 ORDER BY id')
    if cursor.fetchone()[0] != 0:
        return True
    else:
        return False

#______________________________________________________________________________
def dabaseIsEmpty():
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) FROM nodes')
    if cursor.fetchone()[0] == 0:
        return True
    else:
        return False

#______________________________________________________________________________
#find all friends fo current person and list them
def extractFriends(currentUserId, level):
    friendBlocks = driver.find_elements_by_class_name("uiProfileBlockContent")
    i =0
    for block in friendBlocks:
        i = i+1
        try:
            personName = block.find_element_by_tag_name("a").text
            friendsLink = block.find_element_by_class_name("_39g5").get_attribute("href")
            friendId = insertNode(db, personName, friendsLink, level -1)
            print(i, end="\t")
            insertEdge(db, currentUserId, friendId)
        except BaseException as e:
            print(str(personName + ": " + str(e) ))
    setTouched(currentUserId)
#______________________________________________________________________________
def saveNodes():
    cursor = db.cursor()
    cursor.execute('SELECT * FROM nodes ORDER BY id')
    nodes = cursor.fetchall()
    with open('nodes.csv', 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(["id", "label", "address", "a", "b"])
        for node in nodes:
            spamwriter.writerow(node)
            #print("Node: " + str(node[0]) + ": "+ str(node[1]))
    
#______________________________________________________________________________
def saveEdges():
    cursor = db.cursor()
    cursor.execute('SELECT * FROM edges ORDER BY source, target')
    edeges = cursor.fetchall()
    with open('edeges.csv', 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(["Source", "Target"])
        for edege in edeges:
            spamwriter.writerow(edege)
            #print("Edge: " + str(edege[0]) + ": "+ str(edege[1]))
    
#______________________________________________________________________________
#______________________________________________________________________________

pwd = os.getcwd()

with open(pwd + '/conf.json') as data_file:    
    data = json.load(data_file)

if data["use_proxy"]:
    proxy = Proxy({
        'proxyType': ProxyType.MANUAL,
        'httpProxy': '',
        'ftpProxy': '',
        'sslProxy': '',
        'socksProxy': data["proxy"],
        'noProxy': '' # set this value as desired
        })

out_gml = pwd + "/" + data["output"] + ".gml"

friendList = []

graph = nx.Graph()

print ("Starting...")

firefox_profile = webdriver.FirefoxProfile()
firefox_profile.add_extension( pwd + "/quickjava-2.0.6-fx.xpi")
firefox_profile.set_preference("thatoneguydotnet.QuickJava.curVersion", "2.0.6.1") ## Prevents loading the 'thank you for installing screen'
firefox_profile.set_preference("thatoneguydotnet.QuickJava.startupStatus.Images", 2)  ## Turns images off
firefox_profile.set_preference("thatoneguydotnet.QuickJava.startupStatus.Images", 2)  ## Turns images off
firefox_profile.set_preference("thatoneguydotnet.QuickJava.startupStatus.AnimatedImage", 2)  ## Turns animated images off
firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false') ## Turns flash plugin off

#firefox_profile.set_preference("network.cookie.cookieBehavior", 2)
#firefox_profile.set_preference("network.proxy.type", 1);
#firefox_profile.set_preference("network.proxy.http", "mydas.ir");
#firefox_profile.set_preference("network.proxy.http_port", 3128);
#firefox_profile.set_preference("network.proxy.ssl", "mydas.ir");
#firefox_profile.set_preference("network.proxy.ssl_port", 3128);

if data["use_proxy"]:
    driver = webdriver.Firefox(proxy=proxy,firefox_profile=firefox_profile)
else:
    driver = webdriver.Firefox(firefox_profile=firefox_profile)
#driver.implicitly_wait(15)

#................................................

driver.get( "http://www.facebook.com")
#time.sleep(15)


assert "Facebook" in driver.title

print ("Authenticating...")

elem = driver.find_element_by_id("email");
elem.send_keys(data["email"])

elem = driver.find_element_by_id("pass")
elem.send_keys(data["password"])
elem.send_keys(Keys.RETURN)

time.sleep(15)

#................................................

db = createDatabase()

print("There is some data in database:")
response = "s"
if not dabaseIsEmpty():
    response = input("Resume (r) or Restart (s) Export Existing Data (e): ")
if response == "s":
    clearDatabase()
    address = getMainUserFriendsListAddress()
    currentUserId = insertNode(db, getUserName(), address, 2)
    loadPageCompletely(address)
    extractFriends(currentUserId, 2)

#................................................
if response != "e":
    while hasUntouchedRow():
        row = getUntouchedRow()
        print()
        if row[3]>0:
            print("Fetching Friends Of: "+ str(row[0]) +": "+ str(row[1]) +": "+row[2])
            loadPageCompletely(row[2])
            extractFriends(row[0], row[3])
            setTouched(row[0])
        else:
            print("Level Limitation For: "+ row[1])
            setTouched(row[0])
    
#................................................

saveNodes()
saveEdges()

exit()
#______________________________________________________________________________
