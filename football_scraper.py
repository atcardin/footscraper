import requests
import sys
from bs4 import BeautifulSoup

############################################# TODO: change output functions ##################################################
class Person:
    def __init__(self, name = "", date_of_birth = "", nationality = "", role = "", number = ""):
        self.name = name
        self.date_of_birth = date_of_birth
        self.nationality = nationality 
        self.role = role
        self.number = number
    def __str__(self): # called when we print the class
        return "Name: " + self.name + " Date of birth: " + self.date_of_birth + " Nationality: " + self.nationality + " Role: " + self.role + " Number: " + self.number

class Goal:
    def __init__(self, scorer, minute, is_autogoal):
        self.scorer = scorer
        self.minute = minute
        self.is_autogoal = is_autogoal
    def __str__(self):
        return "Scorer: " + self.scorer + " Minute: " + str(self.minute) + " Autogoal: " + self.is_autogoal
    def __repr__(self):
        return "Scorer: " + self.scorer + " Minute: " + str(self.minute) + " Autogoal: " + self.is_autogoal

class Match:
    def __init__(self, round = "", team_1 = "", team_2 = "", score_team_1 = 0, score_team_2 = 0, goals = []):
        self.round = round
        self.team_1 = team_1
        self.team_2 = team_2
        self.score_team_1 = score_team_1
        self.score_team_2 = score_team_2
        self.goals = goals
    def __str__(self):
        out = "Round: " + self.round + " Teams: " + self.team_1 + " - " + self.team_2 + " Score: " + str(self.score_team_1) + " - " + str(self.score_team_2)
        for goal in self.goals:
            out = out + '\n' + repr(goal) 
        return out 

class Team:
    def __init__(self, name = "", stadium = "", coach = "", players = [], matches = [], standing = ""):
        self.name = name
        self.stadium = stadium
        self.coach = coach
        self.players = players
        self.matches = matches
        self.standing = standing
    def __str__(self):
        return self.name + " " + self.stadium + " " + self.coach + " " + self.players + " " + self.matches + " " + self.standing

####################################################################################################################################

def scraper(league_id, league_path, season, out_name = None, debug = False):
    global LEAGUE_ID
    global LEAGUE_PATH
    global SEASON
    global BASE_ADDRESS
    global SEASON_URL
    global HEADERS
    global DEBUG
    global S
    global teams
    global players
    global matches

    if out_name == None:
        out_name = league_id + "_" + season + ".sql"
    
    LEAGUE_ID = league_id
    LEAGUE_PATH = league_path
    SEASON = season
    BASE_ADDRESS = "https://www.transfermarkt.com"
    SEASON_URL = LEAGUE_PATH + "/startseite/wettbewerb/" + LEAGUE_ID + "/saison_id/" + SEASON
    HEADERS = {'User-Agent':'Mozilla/5.0'}
    DEBUG = debug

    teams = []
    players = []
    matches = []

    try:
        with requests.Session() as S: # using a permanent session allows faster responses
            soup = get_soup(BASE_ADDRESS + SEASON_URL)
            partial_homepage_links = soup.find("div", class_="large-8 columns").div.next_sibling.next_sibling.find_all("td", class_="zentriert no-border-rechts")
            partial_matches_links = soup.find("div", class_="box tab-print").div.find("div", class_="grid-view").find_all("td", class_="zentriert no-border-rechts")
            teams_homepage_links = fetch_links(partial_homepage_links)
            teams_matches_links = fetch_links(partial_matches_links)

            extract_players(teams_homepage_links) # creates a list with all the players of the season
            for i in range(len(players)):
                print(players[i])
            
            extract_matches(teams_matches_links) # creates a list with all the matches
            for i in range(len(matches)):
                print(matches[i])
            

    except Exception as e:
        print("Error occurred:", e)
        return False
    return True

###################################################################################################################################################

def extract_goals(match_box):
    goals = []
    goal_soup = get_soup(BASE_ADDRESS + match_box.find("a", class_="ergebnis-link")['href'])
    event_boxes = goal_soup.find("div", class_="sb-ereignisse", id="sb-tore")
    if event_boxes != None: # in some minor leagues's matches goals are not recorded
        for goal_box in event_boxes.find_all("div", class_="sb-aktion"): # for every event box in the goal table
            goals.append(extract_goal(goal_box))
    return goals

def extract_goal(goal_box):
    scorer = goal_box.find("div", class_="sb-aktion-aktion").a['title'] 
    is_autogoal = "True" if goal_box.find("div", class_="sb-aktion-aktion").text.split(',', 2)[1].split(' ',2)[1] == "Own-goal\n" else "False"
    minute_box = goal_box.find("span", class_="sb-sprite-uhr-klein")
    coordinates = minute_box['style'].replace("px", '').replace('-', '').replace(';','').split()
    minute_string = minute_box.string.split("+",2)
    supp = 0
    if len(minute_string) == 2:
        supp = int(minute_string[1])    
    minute = int(int(coordinates[1])/36 + int(coordinates[2])/36*10 + 1) + supp
    return Goal(scorer, minute, is_autogoal)


def extract_matches(teams_matches_links):
    for link in teams_matches_links:
        soup = get_soup(link)
        main_team = soup.find("meta", attrs = {"name" : "keywords"})['content'].split(',',2)[0]
        for box in soup.find("a", attrs = {"href" : SEASON_URL}).parent.parent.parent.find("div", class_="responsive-table").table.tbody.find_all("tr"):
            match = extract_match_from_box(main_team, box)
            if find_match(match) == -1:
                matches.append(match)
                if DEBUG: print(matches[len(matches)-1])
        
def extract_match_from_box(main_team, box):
    goals = extract_goals(box)
    round = box.td.a.string.strip()
    score = box.find("a", class_="ergebnis-link")
    score_1 = score.span.text[0] if score != None else '0'
    score_2 = score.span.text[2] if score != None else '0'
    if box.find("td", class_="zentriert hauptlink").text == 'H':
        team_1 = main_team
        team_2 = box.find("td", class_="zentriert no-border-rechts").a['title']
    if box.find("td", class_="zentriert hauptlink").text == 'A':
        team_1 = box.find("td", class_="zentriert no-border-rechts").a['title']
        team_2 = main_team
    return Match(round, team_1, team_2, score_1, score_2, goals)

def find_match(match):
    for i in range(len(matches)):
        if match.round == matches[i].round and match.team_1 == matches[i].team_1 and match.team_2 == matches[i].team_2 and match.score_team_1 == matches[i].score_team_1 and match.score_team_2 == matches[i].score_team_2:
            return i
    return -1

def extract_players(teams_homepage_links):
    for link in teams_homepage_links:
        soup = get_soup(link)
        for player_box in soup.find_all("td", class_="posrela"):
            player = extract_player_from_box(player_box.parent)
            if find_player(player) == -1:
                players.append(player)
            if DEBUG: print(players[len(players)-1])

def extract_player_from_box(player_box):
    # get_soup(BASE_ADDRESS + player_box.find("div", class_="di nowrap").a['href']) # soup of a single player web page      
    name = player_box.find("div", class_="di nowrap").a['title']
    number = player_box.find("div", class_="rn_nummer").text
    role = player_box.td["title"].capitalize()
    nationality = player_box.find_all("td", class_="zentriert")[2].img['title']
    birthdate = player_box.find_all("td", class_="zentriert")[1].string
    if birthdate == None or birthdate == "- (-)":
        birthdate = ""
    else:
        birthdate = birthdate[0:len(birthdate)-5]
    return Person(name, birthdate, nationality, role, number)

def find_player(player):
    for i in range(len(players)):
        if player.name == players[i].name and player.date_of_birth == players[i].date_of_birth and player.nationality == players[i].nationality:
            return i
    return -1

def get_soup(link):
    r = S.get(link, headers = HEADERS)
    while not r.ok:
        r = S.get(link, headers = HEADERS)    
    return BeautifulSoup(r.text, 'html.parser')

def fetch_links(partial_links):
    links = []
    for partial_link in partial_links:
        links.append(BASE_ADDRESS + partial_link.a['href'])
    return links

