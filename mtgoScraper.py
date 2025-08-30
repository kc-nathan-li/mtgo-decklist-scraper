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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC  # noqa: F401
from selenium.webdriver.support.wait import WebDriverWait  # noqa: F401

from config import (
    standardKeyCardList,
    pioneerKeyCardList,
    scryKeepCols,
    mtgColourComboNameDict,
    mtgKeyToArchetypeDict,
)

import logging

## Bulk Scryfall API


class oracle:
    def bulk():
        scryfallUrl = "https://api.scryfall.com/bulk-data"
        response = requests.get(scryfallUrl)
        bulkDataUrl = response.json()["data"][0]["download_uri"]
        response2 = requests.get(bulkDataUrl)
        oracleJson = response2.json()
        oracleDf = pd.json_normalize(oracleJson)
        return oracleDf

    def clean():
        oracleDf = oracle.bulk()
        oracleDf = oracleDf[~oracleDf["layout"].str.contains("art_series")]
        oracleDf = oracleDf[~oracleDf["layout"].str.contains("token")]
        oracleDf = oracleDf[~oracleDf["set_type"].str.contains("funny")]
        oracleDf["name"] = oracleDf["name"].str.split(" // ").str[0]
        oracleDf["name"] = oracleDf["name"].str.split("/").str[0]
        return oracleDf

    def expand_faces(row):
        if isinstance(row.get("card_faces"), list):
            front = row["card_faces"][0]
            back = row["card_faces"][1] if len(row["card_faces"]) > 1 else {}
            row["mana_cost"] = front.get("mana_cost")
            row["type_line"] = front.get("type_line")
            row["oracle_text"] = front.get("oracle_text")
            row["back_name"] = back.get("name")
            x = back.get("type_line")
            row["back_type_line"] = x
            if "Creature" in x:
                row["back_power"] = back.get("power")
                row["back_toughness"] = back.get("toughness")
            row["back_type_line"] = back.get("type_line")
            row["back_oracle_text"] = back.get("oracle_text")
        return row

    def expandedClean():
        oracleDf = oracle.clean()
        oracleDf["colors"] = oracleDf["colors"].fillna(oracleDf["color_identity"])
        oracleDf = oracleDf.apply(oracle.expand_faces, axis=1)
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
        logging.info(f"Searching for {format} deck lists, {year}-{month:02d}.")
        deckListUrl = f"https://www.mtgo.com/decklists/{year}/{month:02d}?filter={format.capitalize()}"
        reqGet = requests.get(deckListUrl)
        decklistPage = bs4.BeautifulSoup(reqGet.text, "html.parser")
        decklistSelects = decklistPage.select("a.decklists-link")
        tournamentLists = [x for x in decklistSelects if format in x["href"]]
        tournInfoList = []
        for tag in tournamentLists:
            date_str = tag.select_one("time")["datetime"]
            date_obj = dt.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            tournName = f"{date_obj.date()} {tag.select_one('h3').text.strip()}"
            tournUrl = tag["href"]
            tournInfoList.append(
                {"name": tournName, "date": date_obj.date(), "url": tournUrl}
            )
        return tournInfoList

    def getDecksFromUrlScrape(url: str):
        """_summary_

        Args:
            url (str): MTGO Tournament Results URL

        Returns:
            _type_: Dictionary where the key is a deck, the value is a dictionary of size 2, with main board and side board.
        """
        logging.info(
            f"{url} not found. Getting decks from web-page https://www.mtgo.com{url}"
        )
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--blink-settings=imagesEnabled=false")
        driver = webdriver.Chrome()
        driver.get(f"https://www.mtgo.com{url}")
        deckLen = len(driver.find_elements(By.CSS_SELECTOR, '[id*="Decklist"]'))
        mainDecks = [
            driver.find_element(
                by=By.CSS_SELECTOR,
                value=f"#decklist{i}Decklist > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)",
            ).text
            for i in range(deckLen)
        ]
        sideBoards = [
            driver.find_element(
                by=By.CSS_SELECTOR,
                value=f"#decklist{i}Decklist > div:nth-child(2) > div:nth-child(1) > ul:nth-child(4)",
            ).text
            for i in range(deckLen)
        ]
        driver.quit()
        deckDict = {}
        for i in range(deckLen):
            deckDict[f"Deck {i}"] = {"main": mainDecks[i], "side": sideBoards[i]}
        if deckDict != {}:
            json.dump(
                deckDict, open(f"MTGO Decklists Scraped/{url.split('/')[2]}.json", "w")
            )
        return deckDict

    def getDecksFromUrlLoad(url: str):
        logging.info(f"Trying to load {url} from previously downloaded  decklist.")
        return json.load(open(f"MTGO Decklists Scraped/{url.split('/')[2]}.json"))

    def getDecksFromUrl(url: str):
        try:
            outDict = mtgoScrape.getDecksFromUrlLoad(url)
            logging.info(f"{url} load success.")
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
            if "(" in eachLine:
                deckString.remove(eachLine)
            elif "Cards" in eachLine:
                deckString.remove(eachLine)
            else:
                pass
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
        mainDeck = deckDict["main"]
        sideDeck = deckDict["side"]
        mainDeck = mtgoScrape.deckStringCleaner(mainDeck)
        sideDeck = mtgoScrape.deckStringCleaner(sideDeck)
        mainDf = pd.DataFrame.from_dict(
            mainDeck, orient="index", columns=["Quantity"]
        ).sort_values("Quantity", ascending=False)
        mainDf["Card Name"] = mainDf.index
        mainDf["Main/Side"] = "Main"
        mainDf = mainDf.reset_index(drop=True)
        sideDf = pd.DataFrame.from_dict(
            sideDeck, orient="index", columns=["Quantity"]
        ).sort_values("Quantity", ascending=False)
        sideDf["Card Name"] = sideDf.index
        sideDf = sideDf.reset_index(drop=True)
        sideDf["Main/Side"] = "Side"
        outDf = pd.concat([mainDf, sideDf]).reset_index(drop=True)
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
            tempDf["Deck"] = eachDeck
            deckLists += [tempDf]
        outDf = pd.concat(deckLists).reset_index(drop=False)
        outDf = outDf.set_index(["Deck", "Main/Side", "Card Name"])
        return outDf

    def getDeckListsFromUrlList(listOfUrls: list):
        """_summary_

        Args:
            listOfUrls (list): _description_

        Returns:
            DataFrame: DataFrame of all decks in urllist
        """
        resultsLists = []
        for eachUrl in listOfUrls:
            tempDict = mtgoScrape.getDecksFromUrl(eachUrl)
            tempDf = mtgoScrape.getDeckListsFromResults(tempDict)
            tempDf["Deck URL"] = eachUrl
            resultsLists += [tempDf]
        outDf = pd.concat(resultsLists).reset_index(drop=False)
        outDf = outDf.set_index(["Deck URL", "Deck", "Main/Side", "Card Name"])
        outDf = outDf.drop(columns=["index"])
        outDf = outDf.reset_index()
        outDf["Card Name"] = outDf["Card Name"].str.split(" // ").str[0]
        outDf["Card Name"] = outDf["Card Name"].str.split("/").str[0]
        outDf = outDf.set_index(["Deck URL", "Deck", "Main/Side", "Card Name"])
        outDf = outDf.sort_index()
        return outDf

    def removeCardIndex(deckDf):
        deckDf = deckDf.reset_index()
        deckDf = deckDf.set_index(["Deck URL", "Deck"])
        deckDf = deckDf.sort_index()
        return deckDf

    def setDecksToClasses(deckDf, qf):
        deckDf = mtgoScrape.removeCardIndex(deckDf)
        deckDf = identifyDeck.enrichDataFrame(
            deckDf.reset_index(), oracle.expandedClean()
        )
        deckDf = deckDf.set_index(["Deck URL", "Deck"])
        decklists = list(deckDf.index.unique())
        deckObjectList = []
        for eachDeck in decklists:
            tempDeckObj = Deck(deckDf.loc[eachDeck], qf)
            deckObjectList.append(tempDeckObj)
        return deckObjectList

    def mtgoScrapeMain(listOfUrls: list, qf):
        deckDf = mtgoScrape.getDeckListsFromUrlList(listOfUrls)
        return mtgoScrape.setDecksToClasses(deckDf, qf)


class identifyDeck:
    custom_order = ["W", "U", "B", "R", "G"]
    order_map = {color: i for i, color in enumerate(custom_order)}

    def sort_colors(colors):
        return sorted(colors, key=lambda x: identifyDeck.order_map.get(x, float("inf")))

    def dedupe_preserve_order(seq):
        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    def getDeckColour(deckDf):
        result = "".join(
            [c for sublist in deckDf["mana_cost"] for c in sublist if c in "WUBRG"]
        )
        x = identifyDeck.sort_colors(identifyDeck.dedupe_preserve_order(result))
        return "".join(x)

    def checkCardInDeck(cardName, deckDf):
        if len(deckDf[deckDf["Card Name"] == cardName]) == 0:
            return False
        else:
            return True

    def enrichDataFrame(deckDf, oracleDf):
        deckDf = deckDf.reset_index(drop=True)
        deckDf = pd.merge(
            deckDf,
            oracleDf[scryKeepCols],
            left_on="Card Name",
            right_on="name",
            how="left",
        )
        deckDf = deckDf.drop(columns=["name"])
        return deckDf


class dataAnalysis:
    @staticmethod
    def __init__(self):
        return

    def deckComparisonPrep(deck1, deck2):
        deck1 = deck1.reset_index()
        deck2 = deck2.reset_index()
        merged = pd.merge(deck1, deck2, how="outer")
        merged = merged.pivot(
            index="Card Name", columns=["Deck URL", "Deck"], values="Quantity"
        )
        return merged

    def expand_faces(row):
        if isinstance(row.get("card_faces"), list):
            front = row["card_faces"][0]
            back = row["card_faces"][1] if len(row["card_faces"]) > 1 else {}
            row["mana_cost"] = front.get("mana_cost")
            row["type_line"] = front.get("type_line")
            row["oracle_text"] = front.get("oracle_text")
            row["back_name"] = back.get("name")
            x = back.get("type_line")
            row["back_type_line"] = x
            if "Creature" in x:
                row["back_power"] = back.get("power")
                row["back_toughness"] = back.get("toughness")
            row["back_type_line"] = back.get("type_line")
            row["back_oracle_text"] = back.get("oracle_text")
        return row

    def getJaccardForPair(deck1id, deck2id, mainDf):
        deck1 = mainDf.loc[deck1id].sort_index()
        deck2 = mainDf.loc[deck2id].sort_index()
        df = dataAnalysis.deckComparisonPrep(deck1, deck2)
        df = df.fillna(0)
        df["Union"] = df[[deck1id, deck2id]].max(axis=1)
        df["Intersect"] = df[[deck1id, deck2id]].min(axis=1)
        jaccardVal = df["Intersect"].sum() / df["Union"].sum()
        return jaccardVal

    def getDeckLists(df):
        return df.index.unique()

    def jaccardMain(listOfUrls: list):
        deckDf = mtgoScrape.getDeckListsFromUrlList(listOfUrls)
        deckDf = mtgoScrape.removeCardIndex(deckDf)
        decklist = dataAnalysis.getDeckLists(deckDf)
        return decklist


class Queries:
    def __init__(self):
        return

    def filterArchetype(decks, archetypeName, mainSide):
        filteredDecks = [
            deck.deckDf[deck.deckDf["Main/Side"] == mainSide]
            for deck in decks
            if deck.deckName == archetypeName
        ]
        df = pd.concat(filteredDecks)
        df = df.reset_index()
        return df

    def avgArchetype(decks, archetypeName, mainSide):
        filteredDecks = [
            deck.deckDf[deck.deckDf["Main/Side"] == mainSide]
            for deck in decks
            if deck.deckName == archetypeName
        ]
        df = pd.concat(filteredDecks)
        tempDf = df.reset_index()
        tempDf = tempDf.groupby("Card Name")["Quantity"].sum().sort_values(
            ascending=False
        ) / len(filteredDecks)
        return df
    
    def aggArchetype(decks, archetypeName, mainSide):
        filteredDecks = [
            deck.deckDf[deck.deckDf["Main/Side"] == mainSide]
            for deck in decks
            if deck.deckName == archetypeName
        ]
        df = pd.concat(filteredDecks)
        tempDf = df.reset_index()
        tempDf = tempDf.groupby("Card Name")["Quantity"].sum().sort_values(
            ascending=False)
        return df

    def filterDecksWithCard(
        decks, includedCards, mainSide1, excludedCards, mainSide2, mainSide
    ):
        filteredDecks = [
            deck.deckDf[deck.deckDf["Main/Side"] == mainSide]
            for deck in decks
            if all(card in deck.uniqueCards[mainSide1] for card in includedCards)
            if not any(card in deck.uniqueCards[mainSide2] for card in excludedCards)
        ]
        df = pd.concat(filteredDecks)
        df = df.reset_index()
        return df

    def avgDecksWithCard(
        decks, includedCards, mainSide1, excludedCards, mainSide2, mainSide
    ):
        filteredDecks = [
            deck.deckDf[deck.deckDf["Main/Side"] == mainSide]
            for deck in decks
            if all(card in deck.uniqueCards[mainSide1] for card in includedCards)
            if not any(card in deck.uniqueCards[mainSide2] for card in excludedCards)
        ]
        df = pd.concat(filteredDecks)
        df = df.reset_index()
        df = round(
            df.groupby("Card Name")["Quantity"].sum().sort_values(ascending=False)
            / len(filteredDecks),
            2,
        )
        return df

    def aggDecksWithCard(
        decks, includedCards, mainSide1, excludedCards, mainSide2, mainSide
    ):
        filteredDecks = [
            deck.deckDf[deck.deckDf["Main/Side"] == mainSide]
            for deck in decks
            if all(card in deck.uniqueCards[mainSide1] for card in includedCards)
            if not any(card in deck.uniqueCards[mainSide2] for card in excludedCards)
        ]
        df = pd.concat(filteredDecks)
        df = df.reset_index()
        df = round(
            df.groupby("Card Name")["Quantity"].sum().sort_values(ascending=False),
            2,
        )
        return df

class Deck:
    def __init__(self, deckDataFrame, qf):  # qf = Query Format
        keyCardMapping = {
            "standard": standardKeyCardList,
            "pioneer": pioneerKeyCardList,
        }
        keyCards = keyCardMapping.get(qf)
        deckDataFrame = deckDataFrame.sort_values(by="Quantity", ascending=False)
        self.deckDf = deckDataFrame
        self.uniqueCards = {
            "Main": list(
                deckDataFrame[deckDataFrame["Main/Side"] == "Main"]["Card Name"]
            ),
            "Side": list(
                deckDataFrame[deckDataFrame["Main/Side"] == "Side"]["Card Name"]
            ),
        }
        self.deckId = deckDataFrame.index.unique()[0]
        self.colour = mtgColourComboNameDict[identifyDeck.getDeckColour(self.deckDf)]
        self.keyCard = [x for x in keyCards if x in self.uniqueCards['Main']]
        self.landcount = int(
            deckDataFrame[deckDataFrame["type_line"].str.contains("Land")][
                "Quantity"
            ].sum()
        )
        self.avgcmc = float(
            deckDataFrame[~deckDataFrame["type_line"].str.contains("Land")][
                "cmc"
            ].mean()
        )
        try:
            self.archetype = mtgKeyToArchetypeDict[self.keyCard[0]]
        except IndexError:
            if self.landcount < 22:
                self.archetype = "Aggro"
            elif self.landcount > 26:
                self.archetype = "Control"
            else:
                self.archetype = ""
        self.deckName = f"{self.colour} {self.archetype}"
        return
