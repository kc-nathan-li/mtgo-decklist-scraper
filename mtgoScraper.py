## Imports

import datetime as dt
import json
import re

import bs4
import matplotlib.pyplot as plt
import pandas as pd
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

## Temp variables, to add to interface after

queryMonth = 8
queryYear = 2025
queryFormat = "standard"

## Bulk Scryfall API
scryfallUrl = "https://api.scryfall.com/bulk-data"

response = requests.get(scryfallUrl)
bulkDataUrl = response.json()["data"][0]["download_uri"]
response2 = requests.get(bulkDataUrl)
oracleJson = response2.json()
oracleDf = pd.json_normalize(oracleJson)

## MTGO Decklists


class mtgoScrape:
    """Class for functions related to MTGO Scraping decklists
    """
    def __init__(self):
        return

    def formatDeckList(format: str, year, month):
        """_summary_

        Args:
            format (str): MTG Format
            year (_type_): Year to search for decks
            month (_type_): Month to search for decks

        Returns:
            _type_: List of dicts for each tournament, with a 'name', 'date', 'url list
        """
        deckListUrl = f"https://www.mtgo.com/decklists/{year}/{month:02d}?filter={format.capitalize()}"
        reqGet = requests.get(deckListUrl)
        decklistPage = bs4.BeautifulSoup(reqGet.text, "html.parser")
        decklistSelects = decklistPage.select("a.decklists-link")

        standardLists = [x for x in decklistSelects if "standard" in x["href"]]
        tournInfoList = []
        for tag in standardLists:
            date_str = tag.select_one("time")["datetime"]
            date_obj = dt.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")

            tournName = f"{date_obj.date()} {tag.select_one('h3').text.strip()}"

            tournUrl = tag["href"]

            tournInfoList.append(
                {"name": tournName, "date": date_obj.date(), "url": tournUrl}
            )

        return tournInfoList
