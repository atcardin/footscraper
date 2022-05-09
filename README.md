# Footscraper
Web scraper that collects football data from national football competitions on [Transfermarkt](www.transfermarkt.com).
To use the program just import scraper from football_scraper into your fileand then call it:

`scraper(league_id, league_path, season, out_name, debug)`

- `league_id` and `league_path`: arguments used to specify the desired competition to scrape data from, if left empty they get set to IT1 and /serie-a
- `season`: parameter used to choose the wanted season, equal to the year it started (e.g. for season 2009-2010 the parameter required would be 2009), if no value is specified 2020 is assigned.
- `out_name`: field used to specify the name of the output file the program will create, if no name is given it will default to league_id_season.sql
- `debug`: can be set to True, to print on screen additional information during the execution of the program to more easily individuate problems, or to False, which is also the default value, to execute the function normally.
