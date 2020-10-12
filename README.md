# NBA_BballRef_scrape
## NBA statistics and python file for scraping stats from basketball-reference.com

Run nba_scrape.py to gather Seasonal player statistics, averages, draft records, game results, and 
seasonal standings.  The program will create directories for each group of statistics:

<br>Averages<br>
    |__ League average statistics for each season<br>
Drafts<br>
    |__ Each year's draft<br>
Games<br>
    |__ Basic game information for every NBA game<br>
PlayerStats<br>
    |__ Individual statistics (one file for each category) for each season<br>
Standings<br>
    |__ Standings for each season and general history of the league<br><br>
    
It will take a considerable amount of time to run the first time.  Once the files are loaded, 
running the program will only update the files dependent on the current season.

<br> For details on statistical categories, see the 
[Basketball-Reference Glossary](https://www.basketball-reference.com/about/glossary.html)
