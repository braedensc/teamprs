from urllib.request import Request, urlopen
from pprint import pprint
import pandas as p
from html_table_parser_python3 import HTMLTableParser
import lxml.html
import re
from itertools import chain
from flask import Flask
from datetime import datetime
import json
import concurrent.futures

timeFormats = ['%M:%S.%f', '%H:%M:%S.%f']
MAX_THREADS = 60

#example commented at the bottom


class Athlete:
    def __init__(self, name, link, prs, logo, title, teamType):
        self.name = name
        self.link = link
        self.prs = prs
        self.pr800 = None
        self.pr1500 = None
        self.prMile = None
        self.pr3000 = None
        self.pr5000 = None
        self.pr10000 = None
        self.pr5k = None
        self.pr6k = None
        self.pr8k = None
        self.pr10k = None
        self.time = None
        self.logo = logo
        self.title = title
        self.teamType = teamType

    def __repr__(self):  
        return "Name: %s \n Link: %s \n Logo: %s \n  Type: %s \n Title: %s \n PRS: %s \n\n\n\n"%(self.name, self.link, self.logo, self.teamType, self.title, self.prs)

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)


def getAthleteTimes(profileurl):
    '''
    returns a list of events followed by prs for the given athlete: ex. [800, 1:40, 1500, 5:40]
            Parameters:
                    profileurl (String): The link to the athletes tfrrs page
    '''

    req = Request(profileurl, headers={'User-Agent': 'Mozilla/5.0'})
    page1 = urlopen(req)
    html_bytes1 = page1.read()
    html1 = html_bytes1.decode('utf-8', 'ignore')
    p = HTMLTableParser()
    p.feed(html1)
    return p.tables[0]


 
def getAthletes(teamurl):
    '''
    builds a list of athlete objects which contain all the info needed for each athlete
            Parameters:
                    profileurl (teamurl): The link to the team tfrrs page
    '''

    req = Request(teamurl, headers={'User-Agent': 'Mozilla/5.0'})
    page1 = urlopen(req)
    html_bytes1 = page1.read()
    html1 = html_bytes1.decode('utf-8', 'ignore')
    p = HTMLTableParser()
    p.feed(html1)
    athleteNames = p.tables[0]
    athleteProfiles = getLinksToAthleteProfiles(html1)
    logo = getLogo(html1)
    teamTitle = getTeamTitle(html1)
    athleteList = []
    teamType = getTeamType(html1)
    for i in range(1, len(athleteNames) - 1):
        name = " ".join(athleteNames[i][0].split(", ")[::-1])
        athleteList.append(Athlete(name, athleteProfiles[i - 1], [], logo, teamTitle, teamType))
    name = " ".join(athleteNames[-1][0].split(", ")[::-1])
    athleteList.append(Athlete(name, athleteProfiles[-1], [], logo, teamTitle, teamType))
    return athleteList





def getLinksToAthleteProfiles(html1):
    '''
    returns a list of urls for each athlete in the roster
            Parameters:
                    html1 (String): All the html code on the team roster web page, as a very very long String
    '''

    urllist = re.findall(r"""<\s*A\s*HREF=["']([^=]+)["']""", html1)
    string = '//www.tfrrs.org/athletes/'
    urls = list(filter(lambda x : ('athletes' in x), urllist))
    for i in range(len(urls)):
        urls[i] = urls[i].replace(" ", "")
    return urls


#https://logos.tfrrs.org/(insert team here)
def getLogo(html1):
    '''
    returns the link to the team logo on the tffrs team page
            Parameters:
                    html1 (String): All the html code on the team roster web page, as a very very long String
    '''

    urllist = re.findall(r"""https://logos.tfrrs.org/[^\s<>"]+""", html1)
    for i in range(len(urllist)):
        urllist[i] = urllist[i].replace(" ", "")
    return urllist[0]


def getTeamTitle(html1):
    '''
    returns the name of the team from the tfrrs page ex. Georgia Tech
            Parameters:
                    html1 (String): All the html code on the team roster web page, as a very very long String
    '''

    urllist = re.findall(r"""https://logos.tfrrs.org/[^\s<>"]+.*\n.*\n""", html1)
    teamNameIndex = urllist[0].find("\n")
    teamTitle = urllist[0][teamNameIndex:-6]
    return teamTitle

def getTeamType(html1):
    '''
    returns the type of the team from the tfrrs page: ex. Men's Cross Country
            Parameters:
                    html1 (String): All the html code on the team roster web page, as a very very long String
    '''
    urllist = re.findall(r"""https://logos.tfrrs.org/[^\s<>"]+.*\n.*\n.*\n.*\n""", html1)
    teamTypeIndex = urllist[0].find('actions">')
    teamType = urllist[0][teamTypeIndex + 9:-6]
    return teamType


def buildAthleteList(teamurl):
    '''
    returns a list of of athlete objects which now have a messy array of prs
            Parameters:
                    teamurl (String): link to team tffrs page
    '''

    athleteList = getAthletes(teamurl)
    threads = min(MAX_THREADS, len(athleteList))
    #make new temp table of links here
    tempTable = []
    table = []

    for i in range(len(athleteList)):
        tempTable.append('https:' + str(athleteList[i].link))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        table.append(executor.map(getAthleteTimes, tempTable))
   # for i in range(len(athleteList)):
    #     table = getAthleteTimes('https:' + str(athleteList[i].link))
    table = list(chain.from_iterable(table))
    for i in range(len(athleteList)):
        table[i] = list(chain.from_iterable(table[i]))
        athleteList[i].prs = table[i]
    return athleteList



def setallprs(athleteList):
    '''
    builds the prlists for each athlete for each event. Each event gets its own list of athletes for each team.
    Ex. {Georgia Tech - {prs800: [{name: alan drosky, time: 1:41}]}}
            Parameters:
                    athleteList (list): list of all athletes, as returned from buildAthleteList()
    '''

    for i in range(len(athleteList)):
        try:
            index =  athleteList[i].prs.index('800') + 1
            athleteList[i].pr800 = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('1500') + 1
            athleteList[i].pr1500 = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('MILE') + 1
            athleteList[i].prMile = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('3000') + 1
            athleteList[i].pr3000 = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('5000') + 1
            athleteList[i].pr5000 = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('10,000') + 1
            athleteList[i].pr10000 = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('5K\n\t\n\t\n (XC)') + 1
            athleteList[i].pr5k = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('6K\n\t\n\t\n (XC)') + 1
            athleteList[i].pr6k = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('8K\n\t\n\t\n (XC)') + 1
            athleteList[i].pr8k = athleteList[i].prs[index]
        except ValueError:
            pass
        try:
            index =  athleteList[i].prs.index('10K\n\t\n\t\n (XC)') + 1
            athleteList[i].pr10k = athleteList[i].prs[index]
        except ValueError:
            pass
   # print(athleteList)
    return athleteList


def buildprList(athleteList, distance):
    '''
    returns a list of athletes for an even ranked by their prs
            Parameters:
                    athleteList (list): the list of athletes, as returned from setAllprs()
                    distance (String): the event being compared. ex: "pr800" or "pr10k"
    '''

    listprs = []
    for i in range(len(athleteList)):
        if getattr(athleteList[i], distance, None) is not None:
            listprs.append(athleteList[i])
    listprs = sorted(listprs, key=lambda x: sortprs(getattr(x, distance), timeFormats))

    for i in range(len(listprs)):
        listprs[i].time = getattr(listprs[i], distance)
    return listprs
    
def sortprs(date, formats):
    for frmt in formats:
        try:
            str_date = datetime.strptime(date, frmt)
            return str_date
        except ValueError:
            continue


#Example of how it should work.The /athlete route does this process for each team
#athletes = buildAthleteList('https://www.tfrrs.org/teams/xc/FL_college_m_Miami_FL.html')
#athletes = setallprs(athletes)

#the fetch request does this for each event after the above and then sends it all as one big JSON object to the front-end
#return buildprList(athletes, 'pr8k'))

