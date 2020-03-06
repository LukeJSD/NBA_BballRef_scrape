import json
import pydot
import requests
import os
import io
import numpy as np
import pandas as pd
import unidecode
import string
from pprint import pprint
from datetime import datetime
from urllib.request import urlopen
from bs4 import BeautifulSoup
from itertools import repeat
from math import isnan
import csv
from urllib import parse
from requests_html import HTMLSession
from lxml import html
import datetime
from collections import OrderedDict
from datetime import timedelta

target_directory="C:/Users/luke/Git Projects/Bball_ref_scrape/raw_data/"
categories=["per_game", "totals", "per_poss", "advanced", "per_minute"]
not_avg=["advanced", "per_minute"]
years=[y for y in range(1956, 2021)]
current_year=2020

def make_csv(df, string):
    outname = string+'.csv'
    df.to_csv(target_directory+outname)

def normalize_names(headers, stats):
    names=-1
    for i in range(len(headers)):
        if headers[i]=="Player":
            names=i
            break
    for e in stats:
        if names<len(e):
            e[names]=unidecode.unidecode(e[names])

def scrape_players_stats(year, category):
    try:
        html=urlopen(f"https://www.basketball-reference.com/leagues/NBA_{year}_{category}.html")
    except Exception as e:
        print(e)
        print(year, category)
        return None
    soup=BeautifulSoup(html)
    soup.findAll('tr', limit=2)
    headers = [th.getText() for th in soup.findAll('tr', limit=2)[0].findAll('th')]
    headers = headers[1:]
    rows = soup.findAll('tr')[1:]
    player_stats=[]
    player_stats = [[td.getText() for td in rows[i].findAll('td')]
                for i in range(len(rows))]
    normalize_names(headers, player_stats)
    stats = pd.DataFrame(player_stats, columns = headers)
    stats = stats.loc[:,~stats.columns.duplicated()]
    stats=stats.dropna()
    for col in stats.columns:
        try:
            stats[col]=stats[col].replace("","0.0").astype(float)
        except Exception as e:
            continue
    make_csv(stats, str(year)+"_"+category)
    return stats

def scrape_league_averages(category):
    try:
        html=urlopen(f"https://www.basketball-reference.com/leagues/NBA_stats_{category}.html")
    except Exception as e:
        print(e)
        print(category)
        return None
    soup=BeautifulSoup(html)
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
    make_csv(stats, category+"_average")
    return stats

def scrape_draft(year):
    try:
        html=urlopen(f"https://www.basketball-reference.com/draft/NBA_{year}.html")
    except Exception as e:
        print(e)
        print(year, "Draft")
        return None
    soup=BeautifulSoup(html)
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
    make_csv(stats, str(year)+"_draft")
    return stats

def scrape_standings(year):
    try:
        html=urlopen(f"https://www.basketball-reference.com/leagues/NBA_{year}_standings.html")
    except Exception as e:
        print(year, e)
        return None
    soup=BeautifulSoup(html)
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
    make_csv(stats, "standings_"+str(year))
    return stats

def scrape_results1(url, y):
    html=urlopen(url)
    soup=BeautifulSoup(html)
    table=soup.find('table',{'id':'schedule'})
    headers=[c.text.encode('utf-8').strip() for c in table.find('thead').findAll('th')]
    headers.insert(1, "href".encode('utf-8').strip())
    writer = csv.writer(open(f'games{y}.csv', 'w'))
    writer.writerow(headers)
    games=[]
    for c in table.find('tbody').findAll('tr'):
        game=[d.text for d in c.findAll('td')]
        game.insert(0, c.find('th').text)
        game.insert(1, c.find('td',{"data-stat": "box_score_text"}).find("a").get("href"))
        games.append(game)
    writer.writerows(games)

def scrape_results2(url, y):
    try:
        html=urlopen(url)
    except Exception as e:
        return
    try:
        soup=BeautifulSoup(html)
        table=soup.find('table',{'id':'schedule'})
        writer = csv.writer(open(f'games{y}.csv', 'a'))
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

#scrape individual stats from every year in each category
year_stats={}
for year in years:
    year_stats[year]={}
    for cat in categories:
        if year<1974 and cat=="per_poss":
            continue
        file=str(year)+"_"+cat+".csv"
        try:
            df=pd.read_csv(target_directory+file)
            cols=df.columns
            df=df.assign(Yr=year)
            year_stats[year][cat]=df
            #year_stats[year][cat]=pd.read_csv(target_directory+file)
        except FileNotFoundError:
            year_stats[year][cat]=scrape_players_stats(year, cat)
        if year==current_year:
            year_stats[year][cat]=scrape_players_stats(year, cat)
print("Individual Stats Loaded")

#scrape for league wide averages
league_avgs={}
for cat in categories:
    if cat in not_avg:
        continue
    file=cat+"_average"+".csv"
    try:
        league_avgs[cat]=pd.read_csv(target_directory+file)
    except FileNotFoundError:
        league_avgs[cat]=scrape_league_averages(cat)
        #print("File not accessible")
print("League Averages Loaded")

#scrape drafts  
drafts={}
for year in years:
    if year==current_year:
        continue
    file=str(year)+"_draft"+".csv"
    try:
        drafts[year]=pd.read_csv(target_directory+file)
    except FileNotFoundError:
        drafts[year]=scrape_draft(year)
        #print("File not accessible")
print("Drafts Loaded")

#combine all seasons
merged_df={}
for cat in categories:
    temp=[year_stats[y][cat] for y in years if not (cat=="advanced" and y<1985) 
          and not (cat=="per_poss" and y<1974) and type(year_stats[y][cat])==type(pd.DataFrame())]
    ys=[y for y in years if not (cat=="advanced" and y<1985) and not (cat=="per_poss" and y<1974) 
        and type(year_stats[y][cat])==type(pd.DataFrame())]
    df=pd.concat(temp, keys=ys, sort=True)
    df=df.fillna(0.0)
    merged_df[cat]=df
    make_csv(df, "merged_"+cat)
print("Combine all individual seasons Loaded")
    
#career totals
df=merged_df["totals"]
frame=[]
for player in df.drop_duplicates(subset="Player").Player:
    pl=df.loc[df["Player"]==player]
    career=[]
    for col in pl.columns:
        try:
            career.append(sum(pl[col]))
        except Exception as e:
            if col=="Player":
                career.append(player)
            else:
                career.append("N/A")
    career.append(len(pl.drop_duplicates(subset="Yr")))
    frame.append(career)
cols=[col for col in df.columns]
cols.append("Seasons")
career_totals=pd.DataFrame(frame, columns=cols)
make_csv(career_totals, "career_totals")
print("Career Totals Loaded")

#Get full game results for every season
game_results={}
for year in years:
    if year==current_year:
        scrape_results1(f"https://www.basketball-reference.com/leagues/NBA_{year}_games.html", year)
        for month in ["-november", "-december", "-january", "-february", "-march", "-april", "-may", "-june"]:
            scrape_results2(f"https://www.basketball-reference.com/leagues/NBA_{year}_games{month}.html", year)
        game_results[year]=pd.read_csv(f'games{year}.csv')
        continue
    try:
        game_results[year]=pd.read_csv(f'games{year}.csv')
    except Exception as e:
        scrape_results1(f"https://www.basketball-reference.com/leagues/NBA_{year}_games.html", year)
        for month in ["-november", "-december", "-january", "-february", "-march", "-april", "-may", "-june"]:
            scrape_results2(f"https://www.basketball-reference.com/leagues/NBA_{year}_games{month}.html", year)
        game_results[year]=pd.read_csv(f'games{year}.csv')
print("Game Results Loaded")

#Get full standings for every season
standings={}
for year in years:
    if year==current_year:
        standings[year]=scrape_standings(year)
        continue
    file="standings_"+str(year)+".csv"
    try:
        standings[year]=pd.read_csv(target_directory+file)
    except FileNotFoundError:
        standings[year]=scrape_standings(year)
print("Standings Loaded")
        
abrev=pd.read_csv("abreviations.csv")
        
try:
    gen_history=pd.read_csv("gen_hist.csv")
except FileNotFoundError:
    try:
        html=urlopen(f"https://www.basketball-reference.com/leagues/")
    except Exception as e:
        print(e)
    soup=BeautifulSoup(html)
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
    make_csv(stats, "gen_hist")
    gen_history=stats
print("General History Loaded")

print("Done")
