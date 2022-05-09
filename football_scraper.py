import requests
import sys
from bs4 import BeautifulSoup

def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)
    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()        
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()

def get_html(link):
    r = S.get(link, headers = HEADERS)
    while not r.ok:
        r = S.get(link, headers = HEADERS)
    return r.text

def fetch_links(partial_links):
    links = []
    for partial_link in partial_links:
        links.append(BASE_ADDRESS + partial_link.a['href'])
    return links

def fix_role(role):
    if role == "Goalkeeper":
        return "Portiere"
    elif role == "Defender":
        return "Difensore"
    elif role == "midfield":
        return "Centrocampista"
    else:
        return "Attaccante"

def extract_name_from_link(link):
    soup = BeautifulSoup(get_html(link), 'html.parser')
    player = soup.find("h1", attrs={"itemprop" : "name"})
    if player == None: # new website version compatibility
        player = soup.find("h1", class_="data-header__headline-wrapper")
        return {
            "firstname" : player.contents[2][:-1].replace('\n','').replace(' ','') if player.contents[2] != '\n' else player.strong.text,
            "lastname" : player.strong.text if player.contents[2] != '\n' else "null"
        }
    return {
        "firstname" : player.contents[0][:-1] if len(player.contents) > 1 else player.contents[1].string,
        "lastname" : player.contents[1].string if len(player.contents) > 1 else "null"
    }

def extract_player_from_box(player_box, team_name):
    link_player = extract_name_from_link(BASE_ADDRESS + player_box.find("div", class_="di nowrap").a['href'])
    number = player_box.find("div", class_="rn_nummer").text;
    return {
        "role" : fix_role(player_box.td["title"]),
        "number" : number if number != "-" else "null",
        "team" : team_name,
        "birthdate" : fix_birthdate(player_box.find_all("td", class_="zentriert")[1].string),
        "firstname" : link_player["firstname"],
        "lastname" : link_player["lastname"],
        "id" : player_box.find("div", class_="di nowrap").a['href'].split('/',4)[4].zfill(6)
    }

def fix_birthdate(birthdate_raw):
    if birthdate_raw == None or birthdate_raw == "- (-)":
        return "null"
    temp = birthdate_raw.split(",", 2) 
    month_n_day = temp[0].split(" ", 2)
    return "'" + month_n_day[1] + '-' + month_n_day[0].lower() + '-' + temp[1].split(" ", 2)[1] + "'"

def extract_players_from_soup(soup):
    players = []
    team_name = soup.find("h1", attrs={"itemprop" : "name"}).span.text
    for player_box in soup.find_all("td", class_="posrela"):     
        players.append(extract_player_from_box(player_box.parent, team_name))
        if DEBUG: print(players[len(players)-1])
    return players

def extract_team_from_homepage_link(link):
    soup = BeautifulSoup(get_html(link), 'html.parser')
    team = {
        "name" : soup.find("h1", attrs={"itemprop" : "name"}).span.text,
        "city" : find_city(link),
        "coach" : find_main_coach(soup)
    }
    if DEBUG: print(team)
    players = extract_players_from_soup(soup)
    return {
        "team" : team,
        "players" : players
    }

def find_main_coach(soup):
    coaches = soup.find("ul", class_="mitarbeiterVereinSlider slider-list").find_all("li", class_="slider-list")
    stats = coaches[0].find("div", class_="container-hauptinfo")
    if stats == None: # if the season is the current there are no stats on the page
        coach = extract_name_from_link(BASE_ADDRESS + coaches[0].a['href'])
    else:
        max_i = 0
        max = stats.a.text
        for i in range(1, len(coaches)):
            temp = coaches[i].find("div", class_="container-hauptinfo").a.text
            if temp > max:
                max_i = i
                max = temp
        coach = extract_name_from_link(BASE_ADDRESS + coaches[max_i].a['href'])
    return coach['lastname']

def find_city(link):
    link = link.split('/', 8)
    city_link = BASE_ADDRESS + "/" + link[3] + "/datenfakten/verein/" + link[6]
    soup = BeautifulSoup(get_html(city_link), 'html.parser')
    full_address = soup.find("div", class_="large-8 columns")
    residents = full_address.find("span", class_="tabellenplatz")
    if full_address.table.tr == None or full_address.table.tr.next_sibling.next_sibling == None: # for minor leagues, where the team city cannot be found on the website
        return ""
    address = residents.parent.text.split() if residents != None else full_address.table.tr.next_sibling.next_sibling.next_sibling.next_sibling.td.text.split()
    if len(address) == 1: # needed for minor leagues, missing parts of address
        return address[0]
    city_name = address[1]
    for i in range(2, len(address)-2):
        city_name += " " + address[i]
    return city_name

def get_match_from_box(match_box, home_team):
    goal = match_box.find("a", class_="ergebnis-link")
    return {
        "round" : match_box.td.a.string.strip(),
        "home_team" : home_team,
        "away_team" : match_box.find("td", class_="zentriert no-border-rechts").a['title'],
        "goal_home_team" : goal.span.text[0] if goal != None else '0',
        "goal_away_team" : goal.span.text[2] if goal != None else '0'
    }

def get_goal_from_event_box(event_box, match_id, players):
    minute_box = event_box.find("span", class_="sb-sprite-uhr-klein")
    coordinates = minute_box['style'].replace("px", '').replace('-', '').replace(';','').split()
    minute_string = minute_box.string.split("+",2)
    supp = 0
    if len(minute_string) == 2:
        supp = int(minute_string[1])    
    id = find_player_id(event_box.find("div", class_="sb-aktion-aktion").a['title'], players)
    if id == '':
        return None
    return {
        "match_id" : match_id,
        "minute" : int(int(coordinates[1])/36 + int(coordinates[2])/36*10 + 1) + supp,
        "player" : event_box.find("div", class_="sb-aktion-aktion").a['title'],
        "player_id" : id if id != '' else 'null',
        "autogol" : "true" if event_box.find("div", class_="sb-aktion-aktion").text.split(',', 2)[1].split(' ',2)[1] == "Own-goal\n" else "false"
    }

def find_player_id(player_shortname, players):
    for entry in players:
        if entry['lastname'] == '' and entry['firstname'] == player_shortname:  
            return entry['id']
        elif entry['firstname'] + ' ' + entry['lastname'] == player_shortname:
            return entry['id']
    return ''

def extract_matches_goals(match_boxes, players):
    matches = []
    goals = []
    id = 0
    for j in progressbar(range(len(match_boxes)), "Downloading goals: ", 40): # for every link to a team's homepage
        if match_boxes[j]["box"].find("td", class_="zentriert hauptlink").text == 'H': # if the match was played on the home field for the team that's being evaluated, this is needed to avoid duplicates
            match = get_match_from_box(match_boxes[j]["box"], match_boxes[j]['home_team']) # extract the match infos from the box
            if (match['goal_home_team'] != '-' and match['goal_home_team'] != '-'):
                match["id"] = LEAGUE_ID.ljust(4,'0') + str(id).rjust(4,'0') # add an unique id to the match
                matches.append(match)
                if DEBUG: print(match)
                if match["goal_home_team"] != '0' or match["goal_away_team"] != '0': # if there's at least one goal
                    goal_soup = BeautifulSoup(get_html(BASE_ADDRESS + match_boxes[j]["box"].find("a", class_="ergebnis-link")['href']), 'html.parser')
                    mode = goal_soup.find("div", class_="sb-halbzeit")
                    if mode != None and mode.string != "(uncontested)": # in minor leagues there are some missing infos 
                        event_boxes = goal_soup.find("div", class_="sb-ereignisse", id="sb-tore")
                        if event_boxes != None: # in some minor leagues's matches goals are not recorded
                            for goal_box in event_boxes.find_all("div", class_="sb-aktion"): # for every event box in the goal table
                                goal = get_goal_from_event_box(goal_box, match["id"] , players)
                                if goal != None: # skip goals without scorer
                                    while len(goals) > 0 and goal['minute'] == goals[len(goals)-1]['minute'] and goal['match_id'] == goals[len(goals)-1]['match_id']: # goals can't be in the same minute
                                        goal['minute'] += 1
                                    goals.append(goal) #extract goals and add them to the list
                                    if DEBUG: print(goals[len(goals)-1])
            id += 1
    return {
        'matches' : matches,
        'goals' : goals
    }

def extract_teams_and_players(teams_homepage_links):
    teams = []
    players = []
    for j in progressbar(range(len(teams_homepage_links)), "Downloading teams and players: ", 40): # for every link to a team's homepage
        temp = extract_team_from_homepage_link(teams_homepage_links[j]) # extract the team infos and add them to the list
        teams.append(temp['team'])
        for player in temp['players']:
            players.append(player)
    return {
        'teams' : teams,
        'players' : players
    }

def extract_matches_boxes(teams_matches_links):
    match_boxes = []
    i = 0
    for j in progressbar(range(len(teams_matches_links)), "Downloading matches: ", 40): # for every link to a team's matches page
        soup = BeautifulSoup(get_html(teams_matches_links[j]), 'html.parser')
        home_team = soup.find("meta", attrs = {"name" : "keywords"})['content'].split(',',2)[0]
        temp_match_boxes = soup.find("a", attrs = {"href" : SEASON_URL}).parent.parent.parent.find("div", class_="responsive-table").table.tbody.find_all("tr")
        for box in temp_match_boxes[:19]: # ONLY THE FIRST HALF OF THE CHAMPIONSHIP
            match_boxes.append({"box" : box, "home_team" : home_team})
        i += 1
    return match_boxes

def output(teams, players, matches, goals, filename):
    f = open(filename, "w")
    f.write("/* File created by scraping " + BASE_ADDRESS + " using Antonio Cardin's program */\n")
    f.write("\ninsert into Squadre values\n")
    for i in range(len(teams)):
        f.write("  ('" + teams[i]["name"].replace("'", "''") + "','" + teams[i]["city"].replace("'", "''") + "','" + teams[i]["coach"].replace("'", "''") + "')")
        if i != len(teams) - 1:
            f.write(",\n")
        else:
            f.write(";\n")
    f.write("\ninsert into Giocatori values\n")
    for i in range(len(players)):
        f.write("  ('" + players[i]["id"] + "','" + players[i]["team"].replace("'", "''") + "'," + players[i]["number"] + ",'" + players[i]["firstname"].replace("'", "''") + "','" + players[i]["lastname"].replace("'", "''") + "'," + players[i]["birthdate"] + ",'" + players[i]["role"] + "')")
        if i != len(players) - 1:
            f.write(",\n")
        else:
            f.write(";\n")
    f.write("\ninsert into Partite values\n")
    for i in range(len(matches)):
        f.write("  ('" + matches[i]["id"] + "'," + matches[i]["round"] + ",'" + matches[i]["home_team"].replace("'", "''") + "','" + matches[i]["away_team"].replace("'", "''") + "'," + matches[i]["goal_home_team"] + "," + matches[i]["goal_away_team"] + ")")
        if i != len(matches) - 1:
            f.write(",\n")
        else:
            f.write(";\n")
    f.write("\ninsert into Gol values\n")
    for i in range(len(goals)):
        f.write("  ('" + goals[i]["match_id"] + "'," + str(goals[i]["minute"]) + ",'" + goals[i]["player_id"] + "'," + goals[i]["autogol"]  + ")")
        if i != len(goals) - 1:
            f.write(",\n")
        else:
            f.write(";\n")
    f.close()

def player_already_found(player, players):
    for element in players:
        if element["id"] == player["id"]:
            return True
    return False

def fix_duplicates(players):
    fixed_players = []
    for i in range(len(players)):
        if players[i] not in players[i+1:] and not player_already_found(players[i], players[:i]): # MAKE SURE TO REMOVE PLAYERS THAT HAVE CHANGED TEAM
            fixed_players.append(players[i])                                                      # DURING THE SEASON
    return fixed_players

def scraper(league_id = "IT1", league_path = "/serie-a", season = "2020", out_name = None, debug = False):
    global LEAGUE_ID
    global LEAGUE_PATH
    global SEASON
    global BASE_ADDRESS
    global SEASON_URL
    global HEADERS
    global DEBUG
    global S

    if out_name == None:
        out_name = league_id + "_" + season + ".sql"
    
    LEAGUE_ID = league_id
    LEAGUE_PATH = league_path
    SEASON = season
    BASE_ADDRESS = "https://www.transfermarkt.com"
    SEASON_URL = LEAGUE_PATH + "/startseite/wettbewerb/" + LEAGUE_ID + "/saison_id/" + SEASON
    HEADERS = {'User-Agent':'Mozilla/5.0'}
    DEBUG = debug
    try:
        with requests.Session() as S: # using a permanent session allows faster responses
            soup = BeautifulSoup(get_html(BASE_ADDRESS + SEASON_URL), 'html.parser')
            partial_homepage_links = soup.find("div", class_="large-8 columns").div.next_sibling.next_sibling.find_all("td", class_="zentriert no-border-rechts")
            partial_matches_links = soup.find("div", class_="box tab-print").div.find("div", class_="grid-view").find_all("td", class_="zentriert no-border-rechts")
            teams_homepage_links = fetch_links(partial_homepage_links)
            teams_matches_links = fetch_links(partial_matches_links)
            teams_n_players = extract_teams_and_players(teams_homepage_links)
            teams_n_players['players'] = fix_duplicates(teams_n_players['players']) # remove duplicates 
            match_boxes = extract_matches_boxes(teams_matches_links)
            matches_n_goals = extract_matches_goals(match_boxes, teams_n_players['players'])
            output(teams_n_players['teams'], teams_n_players['players'], matches_n_goals['matches'], matches_n_goals['goals'], out_name)
    except Exception as e:
        print("Error occurred:", e)
        return False
    return True


