## Imports

import datetime as dt
import json
import re  # noqa: F401

import bs4
import matplotlib.pyplot as plt  # noqa: F401
import pandas as pd
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException  # noqa: F401
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC  # noqa: F401
from selenium.webdriver.support.wait import WebDriverWait  # noqa: F401

## Temp variables, to add to interface after

queryMonth = 8
queryYear = 2025
queryFormat = "standard"


## Bulk Scryfall API
def bulkOracle():
    scryfallUrl = "https://api.scryfall.com/bulk-data"
    response = requests.get(scryfallUrl)
    bulkDataUrl = response.json()["data"][0]["download_uri"]
    response2 = requests.get(bulkDataUrl)
    oracleJson = response2.json()
    oracleDf = pd.json_normalize(oracleJson)
    return oracleDf


## MTGO Decklists


class mtgoScrape:
    """Class for functions related to MTGO Scraping decklists"""

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
        print(f"Searching for {format} deck lists, {year}-{month:02d}.")
        deckListUrl = f"https://www.mtgo.com/decklists/{year}/{month:02d}?filter={format.capitalize()}"
        reqGet = requests.get(deckListUrl)
        decklistPage = bs4.BeautifulSoup(reqGet.text, "html.parser")
        decklistSelects = decklistPage.select("a.decklists-link")
        tournamentLists = [x for x in decklistSelects if format in x["href"]]
        tournInfoList = []
        for tag in tournamentLists:
            print(tag)
            date_str = tag.select_one("time")["datetime"]
            date_obj = dt.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            tournName = f"{date_obj.date()} {tag.select_one('h3').text.strip()}"
            tournUrl = tag["href"]
            tournInfoList.append(
                {"name": tournName, "date": date_obj.date(), "url": tournUrl}
            )
        return tournInfoList
    
    def getDecksFromUrlScrape(url:str):
        """_summary_

        Args:
            url (str): MTGO Tournament Results URL

        Returns:
            _type_: Dictionary where the key is a deck, the value is a dictionary of size 2, with main board and side board.
        """
        print(f"{url} not found. Getting decks from web-page {url}")
        driver = webdriver.Chrome()
        driver.get(f"https://www.mtgo.com{url}")
        deckLen = len(driver.find_elements(By.CSS_SELECTOR, '[id*="Decklist"]'))
        mainDecks = [driver.find_element(by=By.CSS_SELECTOR, value=f"#decklist{i}Decklist > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)").text for i in range(deckLen)]
        sideBoards = [driver.find_element(by=By.CSS_SELECTOR, value=f"#decklist{i}Decklist > div:nth-child(2) > div:nth-child(1) > ul:nth-child(4)").text for i in range(deckLen)]
        driver.quit()
        deckDict = {}
        for i in range(deckLen):
            deckDict[f"Deck {i}"] = {'main':mainDecks[i], 'side': sideBoards[i]}
        json.dump(deckDict, open(f"MTGO Decklists Scraped/{url.split("/")[2]}.json", 'w'))
        return deckDict
    
    def getDecksFromUrlLoad(url:str):
        print(f"Trying to load {url} from previously downloaded decklist.")
        return json.load(open(f"MTGO Decklists Scraped/{url.split("/")[2]}.json"))

    def getDecksFromUrl(url:str):
        try:
            outDict = mtgoScrape.getDecksFromUrlLoad(url)
            return outDict
        except FileNotFoundError:
            outDict = mtgoScrape.getDecksFromUrlScrape(url)
            return outDict

    def deckStringCleaner(deckString):
        """_summary_

        Args:
            deckDict (_type_): The input is the value of the output dictionary from mtgoScrape.getDecksFromPage, i.e. The dict with 'main' and 'side' keys, and decklist Strings as the values

        Returns:
            _type_: _description_
        """
        outDict = {}
        deckString = deckString.split("\n")
        for eachLine in deckString:
            if "Creature (" in eachLine:
                deckString.remove(eachLine)
            elif "Enchantment (" in eachLine:
                deckString.remove(eachLine)
            elif "Artifact (" in eachLine:
                deckString.remove(eachLine)
            elif "Land (" in eachLine:
                deckString.remove(eachLine)
            elif "Instant (" in eachLine:
                deckString.remove(eachLine)
            elif "Sorcery (" in eachLine:
                deckString.remove(eachLine)
            elif " Cards" in eachLine:
                deckString.remove(eachLine)
            elif "Planeswalker (" in eachLine:
                deckString.remove(eachLine)
            elif "Other" in eachLine:
                deckString.remove(eachLine)
        for eachLine in deckString:
            eachLineSplitUp = eachLine.split(" ")
            outDict[" ".join(eachLineSplitUp[1:])] = int(eachLineSplitUp[0])
        return outDict
    
    def deckCleaner(deckDict):
        """This takes the output from 

        Args:
            deckDict (_type_): Dictionary where there are two keys, 'main' and 'side'

        Returns:
            _type_: _description_
        """
        mainDeck = deckDict['main']
        sideDeck = deckDict['side']
        mainDeck = mtgoScrape.deckStringCleaner(mainDeck)
        sideDeck = mtgoScrape.deckStringCleaner(sideDeck)
        mainDf = pd.DataFrame.from_dict(mainDeck, orient="index", columns=['Quantity']).sort_values('Quantity', ascending=False)
        mainDf['Card Name'] = mainDf.index
        mainDf['Main/Side'] = 'Main'
        mainDf = mainDf.reset_index(drop=True)
        sideDf = pd.DataFrame.from_dict(sideDeck, orient="index", columns=['Quantity']).sort_values('Quantity', ascending=False)
        sideDf['Card Name'] = sideDf.index
        sideDf = sideDf.reset_index(drop=True)
        sideDf['Main/Side'] = 'Side'
        outDf = pd.concat([mainDf,sideDf]).reset_index(drop=True)
        return outDf
    
    def getDeckListsFromResults(decksDict):
        """Takes the output from getDecksFromUrl, which is of the format {"Deck 0": {'main': ..., 'side':...}, "Deck 1": ...}

        Args:
            url (str): _description_

        Returns:
            _type_: _description_
        """
        deckLists = []
        for eachDeck in decksDict:
            tempDf = mtgoScrape.deckCleaner(decksDict[eachDeck])
            tempDf['Deck'] = eachDeck
            deckLists += [tempDf]
        outDf = pd.concat(deckLists).reset_index(drop=False)
        outDf = outDf.set_index(['Deck', 'Main/Side', 'Card Name'])
        return outDf
    
    def getDeckListsFromUrlList(listOfUrls:list):
        resultsLists = []
        for eachUrl in listOfUrls:
            tempDict = mtgoScrape.getDecksFromUrl(eachUrl)
            tempDf = mtgoScrape.getDeckListsFromResults(tempDict)
            tempDf['Deck URL'] = eachUrl
            print(tempDf)
            resultsLists += [tempDf]
        outDf = pd.concat(resultsLists).reset_index(drop=False)
        outDf = outDf.set_index(['Deck URL', 'Deck', 'Main/Side', 'Card Name'])
        outDf = outDf.drop(columns=['index'])
        return outDf

#print(mtgoScrape.getDeckListsFromUrlList(["/decklist/standard-challenge-32-2025-08-1512810049", "/decklist/standard-challenge-32-2025-08-1612810061"]))

augOutput = mtgoScrape.formatDeckList('standard',2025,8)

urlList = [x['url'] for x in augOutput]

print(mtgoScrape.getDeckListsFromUrlList(urlList))

print(augOutput)