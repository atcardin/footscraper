from football_scraper import scraper
from competitions import *
from multiprocessing import Pool

def process_image(competition):
    scraper(league_id = competition['league_id'], league_path = competition['league_path'], season = competition['season'], debug = False)

def main():
    pool = Pool()
    pool.map(process_image, competitions)
    pool.close()

if __name__ == "__main__":
    main()