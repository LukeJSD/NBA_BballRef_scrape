import os
import io
import pandas as pd
import unidecode
import string
from urllib.request import urlopen
from bs4 import BeautifulSoup
import csv

target_directory = '/'.join(os.path.abspath('nba_scrape.py').split('\\')[:-1]) + '/'
categories = ['totals',
              'advanced',
              "per_game",
              "totals",
              "per_poss",
              "advanced",
              "per_minute",
              'adj_shooting',
              'play-by-play',
              'shooting']
current_year = 2020
years = [y for y in range(1956, current_year+1)]
teams = pd.read_csv('abreviations.csv')

if not os.path.exists(target_directory+'/PlayerStats'):
    os.mkdir(target_directory+'/PlayerStats')
if not os.path.exists(target_directory+'/Games'):
    os.mkdir(target_directory+'/Games')
if not os.path.exists(target_directory+'/Standings'):
    os.mkdir(target_directory+'/Standings')
if not os.path.exists(target_directory+'/Drafts'):
    os.mkdir(target_directory+'/Drafts')
if not os.path.exists(target_directory+'/Averages'):
    os.mkdir(target_directory+'/Averages')


def make_csv(df, string, index=False):
    outname = string+'.csv'
    df.to_csv(target_directory+outname, index=index)


def normalize_names(headers, stats):
    names=-1
    for i in range(len(headers)):
        if headers[i]=="Player":
            names=i
            break
    for e in stats:
        if names<len(e):
            e[names]=unidecode.unidecode(e[names])


def handle_subheaders(h, cat):
    drawn = False
    heaves = False
    out = []
    for c in h:
        if cat=='play-by-play':
            if c in ['BadPass', 'LostBall']:
                c += 'TOV'
            elif c in ['Shoot', 'Off.']:
                if drawn:
                    c += 'FoulsCommitted'
                    if c == 'Off.FoulsCommitted':
                        drawn = True
                else:
                    c += 'FoulsDrawn'
        elif cat=='shooting':
            if c=='%FGA':
                c = 'Dunk' + c
            if c=='#':
                if heaves:
                    c = 'Heaves'
                else:
                    c = 'Dunks'
                    heaves = True
            if c=='Att.':
                c = 'Heave' + c
        out.append(c)
    return out


def scrape_players_stats(year, category):
    try:
        html=urlopen(f"https://www.basketball-reference.com/leagues/NBA_{year}_{category}.html")
    except Exception as e:
        print(e)
        print(year, category)
        return None
    soup=BeautifulSoup(html, features="lxml")
    soup.findAll('tr', limit=2)
    if category=='play-by-play' or category=='shooting':
        headers = [th.getText() for th in soup.findAll('tr', limit=2)[1].findAll('th')]
        headers = handle_subheaders(headers, category)
    else:
        headers = [th.getText() for th in soup.findAll('tr', limit=2)[0].findAll('th')]
    headers = headers[1:]
    rows = soup.findAll('tr')[1:]
    player_stats = [[td.getText() for td in rows[i].findAll('td')]
                for i in range(len(rows))]
    simpPos = [ply[1].split('-')[0] for ply in player_stats if len(ply)!=0]
    headers.insert(2, 'BasePos')
    offset=0
    for i in range(len(simpPos)):
        if len(player_stats[i])!=0:
            player_stats[i].insert(2, simpPos[i-offset])
        else:
            offset+=1
    normalize_names(headers, player_stats)
    stats = pd.DataFrame(player_stats, columns=headers)
    stats = stats.loc[:,~stats.columns.duplicated()]
    stats=stats.dropna()
    stats['Year'] = [year] * len(stats)
    for col in stats.columns:
        try:
            stats[col]=stats[col].replace("","0.0").astype(float)
        except Exception as e:
            continue
    stats = stats.join(teams.set_index('Abr'), on='Tm')
    make_csv(stats, 'PlayerStats/'+str(year)+"_"+category)
    return stats


def career_tot():
    totals = pd.DataFrame()
    for year in years:
        df = pd.read_csv(target_directory+f'/PlayerStats/{year}_totals.csv')
        totals = pd.concat([totals, df[df['Tm']!='TOT']])
    ct = totals.groupby('Player').sum()
    ff = totals.groupby(['Player', 'Year']).count().groupby('Player').count()
    ct['Seasons'] = ff.Tm
    for shot in ['FG', '3P', 'FT']:
        ct[f'{shot}%'] = ct[shot]/ct[f'{shot}A']
    ct['eFG%'] = (ct['FG']+0.5*ct['3P'])/ct['FGA']
    ct['TS%'] = (ct['PTS']/(2*(ct['FGA']+0.44*ct['FTA'])))
    make_csv(ct, 'PlayerStats/Career_totals', index=True)


def scrape_league_averages(category):
    try:
        html=urlopen(f"https://www.basketball-reference.com/leagues/NBA_stats_{category}.html")
    except Exception as e:
        print(e)
        print(category)
        return None
    soup=BeautifulSoup(html, features='lxml')
    soup.findAll('tr', limit=2)
    headers = [th.getText() for th in soup.findAll('tr', limit=2)[1].findAll('th')]
    headers = headers[1:]
    rows = soup.findAll('tr')[1:]
    player_stats = [[td.getText() for td in rows[i].findAll('td')]
            for i in range(len(rows))]
    stats = pd.DataFrame(player_stats, columns = headers)
    stats=stats.dropna()
    for col in stats.columns:
        try:
            stats[col]=stats[col].replace("","0.0").astype(float)
        except Exception as e:
            continue
    make_csv(stats, 'Averages/'+category+"_average")
    return stats


def scrape_draft(year):
    try:
        html=urlopen(f"https://www.basketball-reference.com/draft/NBA_{year}.html")
    except Exception as e:
        print(e)
        print(year, "Draft")
        return None
    soup=BeautifulSoup(html, features='lxml')
    soup.findAll('tr', limit=2)
    headers = [th.getText() for th in soup.findAll('tr', limit=2)[1].findAll('th')]
    headers = headers[1:]
    rows = soup.findAll('tr')[1:]
    player_stats = [[td.getText() for td in rows[i].findAll('td')]
            for i in range(len(rows))]
    stats = pd.DataFrame(player_stats, columns = headers)
    stats=stats.dropna()
    for col in stats.columns:
        try:
            stats[col]=stats[col].replace("","0.0").astype(float)
        except Exception as e:
            continue
    make_csv(stats, 'Drafts/'+str(year)+"_draft")
    return stats


def scrape_standings(year):
    try:
        html=urlopen(f"https://www.basketball-reference.com/leagues/NBA_{year}_standings.html")
    except Exception as e:
        print(year, e)
        return None
    soup=BeautifulSoup(html, features="lxml")
    soup.findAll('tr')
    headers = [th.getText() for th in soup.findAll('tr', limit=2)[1].findAll('th')]
    headers = headers[:]
    rows = soup.findAll('tr')[1:]
    player_stats = [[td.getText() for td in rows[i].findAll('td')]
                    for i in range(len(rows))]
    try:
        stats = pd.DataFrame(player_stats, columns = headers)
    except Exception as e:
        player_stats_2=[i for i in player_stats if len(i)==7]
        headers_2=[c for c in headers if c in ['W', 'L', 'W/L%', 'GB', 'PS/G', 'PA/G', 'SRS']]
        stats = pd.DataFrame(player_stats_2, columns = headers_2)
        stats=stats[:30]
    rows = soup.findAll('tr')[:]
    tms = [[td.getText() for td in rows[i].findAll('td')]
                    for i in range(len(rows))]
    tms=[i for i in tms[0] if len(i)>10]
    teams=[]
    for t in tms:
        teams.append("Conference")
        temp=t.find("SRS")
        t=t[temp:]
        buf = io.StringIO(t)
        line=buf.readline()
        start=False
        while not start or not line=="":
            if len(line)<5:
                line=buf.readline()
                continue
            start=True
            for i in range(len(line)):
                if line[i] not in string.ascii_letters and not line[i]==" " and not line[i]==".":
                    if "76ers" in line:
                        temp=line.find("76ers")+5
                    else:
                        temp=i
                    break
            teams.append(line[:temp])
            line=buf.readline()
    try:
        stats.insert(0, "Tm", teams)
    except Exception as e:
        temp=[j for j in teams if "Division" in j or "Conference" in j]
        temp.append("")
        for j in temp:
            teams.remove(j)
        teams=teams[:len(stats)]
        stats.insert(0, "Tm", teams)
    for col in stats.columns:
        try:
            stats[col]=stats[col].replace("","0.0").astype(float)
        except Exception as e:
            continue
    make_csv(stats, 'Standings/'+"standings_"+str(year))
    return stats


def scrape_results1(url, y):
    html=urlopen(url)
    soup=BeautifulSoup(html, features="lxml")
    table=soup.find('table',{'id':'schedule'})
    headers=[c.text.encode('utf-8').strip() for c in table.find('thead').findAll('th')]
    headers.insert(1, "href".encode('utf-8').strip())
    writer = csv.writer(open(f'{target_directory}Games/games{y}.csv', 'w', newline=''))
    writer.writerow(headers)
    games=[]
    covid = False
    for c in table.find('tbody').findAll('tr'):
        game=[d.text for d in c.findAll('td')]
        game.insert(0, c.find('th').text)
        try:
            game.insert(1, c.find('td',{"data-stat": "box_score_text"}).find("a").get("href"))
        except Exception as e:
            if y == 2020:   # Damn covid.
                covid = True
                game.insert(1, None)
            else:
                print(e)
                exit(1)
        games.append(game)
    if covid:
        games.append(['End-Playoffs', None])
    writer.writerows(games)


def scrape_results2(url, y):
    try:
        html=urlopen(url)
    except Exception as e:
        return
    try:
        soup=BeautifulSoup(html, features="lxml")
        table=soup.find('table',{'id':'schedule'})
        writer = csv.writer(open(f'{target_directory}Games/games{y}.csv', 'a', newline=''))
        games=[]
        for c in table.find('tbody').findAll('tr'):
            game=[d.text for d in c.findAll('td')]
            game.insert(0, c.find('th').text)
            try:
                game.insert(1, c.find('td',{"data-stat": "box_score_text"}).find("a").get("href"))
            except Exception as e:
                game.insert(1, None)
            games.append(game)
        writer.writerows(games)
    except Exception as e:
        return None


def yearStats():
    #scrape individual stats from every year in each category
    for year in years:
        for cat in categories:
            if (year<1974 and cat=="per_poss") or (year<1997 and (cat=="play-by-play" or cat=="shooting")) or (cat=='adj_shooting'):
                continue
            file='PlayerStats/'+str(year)+"_"+cat+".csv"
            if not os.path.exists(file) or year == current_year:
                scrape_players_stats(year, cat)
    print("Individual Stats Loaded")
    career_tot()
    print('Career Totals Loaded')


def leagueAvg():
    #scrape for league wide averages
    for cat in categories:
        if cat not in ['per_game', 'totals', 'per_poss']:
            continue
        file='Averages/'+cat+"_average"+".csv"
        if not os.path.exists(file):
            scrape_league_averages(cat)
    print("League Averages Loaded")


def drafts():
    #scrape drafts
    for year in years:
        if year==current_year:
            continue
        file='Drafts/'+str(year)+"_draft"+".csv"
        if not os.path.exists(file):
            scrape_draft(year)
    print("Drafts Loaded")


def gameResults():
    #Get full game results for every season
    for year in years:
        file = f'{target_directory}Games/games{year}.csv'
        if os.path.exists(file) and not year == current_year:
            continue
        scrape_results1(f"https://www.basketball-reference.com/leagues/NBA_{year}_games.html", year)
        for month in ["-november", "-december", "-january", "-february", "-march", "-april", "-may", "-june"]:
            scrape_results2(f"https://www.basketball-reference.com/leagues/NBA_{year}_games{month}.html", year)
    print("Game Results Loaded")


def standing():
    #Get full standings for every season
    for year in years:
        file = 'Standings/'+"standings_"+str(year)+'.csv'
        if not os.path.exists(file) or year == current_year:
            scrape_standings(year)
    print("Standings Loaded")


def genHist():
    try:
        html=urlopen(f"https://www.basketball-reference.com/leagues/")
    except Exception as e:
        print(e)
    soup=BeautifulSoup(html, features="lxml")
    soup.findAll('tr', limit=2)
    headers = [th.getText() for th in soup.findAll('tr', limit=2)[1].findAll('th')]
    headers = headers[1:]
    rows = soup.findAll('tr')[1:]
    player_stats = [[td.getText() for td in rows[i].findAll('td')]
                    for i in range(len(rows))]
    stats = pd.DataFrame(player_stats, columns = headers)
    stats=stats[stats.Lg=="NBA"]
    stats=stats.dropna()
    yrs=years[::-1]
    if len(stats)>len(yrs):
        diff=len(stats)-len(yrs)
        temp=[y for y in range(years[0]-diff, years[0])]
        temp=temp[::-1]
        yrs=yrs+temp
    stats.insert(0, "Yr", yrs)
    make_csv(stats, "Standings/gen_hist")
    print("General History Loaded")


def main():
    yearStats()
    leagueAvg()
    drafts()
    gameResults()
    standing()
    genHist()
    print("Done")


if __name__ == '__main__':
    main()
