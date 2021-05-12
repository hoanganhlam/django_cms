from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from apps.cms.models import PublicationTerm, Publication, Term
import random
import re, json
from bs4.element import Tag, NavigableString


def fetch_date(url, d):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, features="html.parser")
    elms = soup.select(".mw-parser-output")
    heading = None
    out = []
    for child in elms[0].findChildren(recursive=False):
        if child.name == "h2":
            heading = child.select(".mw-headline")[0].find_all(text=True)[0]
        if heading == "Holidays and observances":
            break
        if heading:
            if child.name == "ul":
                for li in child.select("li"):
                    arr = list(li.find_all(text=True))
                    full_text = "".join(arr)
                    arr_text = full_text.split(" – ")
                    year = arr_text[0].strip()
                    if len(arr_text) == 1:
                        arr_text = full_text.split(" - ")
                    if len(arr_text) == 1:
                        continue
                    text_cleaned = re.sub('\[[0-9]*\]', '', arr_text[1].strip())
                    entities = []
                    i = 0
                    for content in li.contents:
                        if content.name == "a" and i > 1:
                            description = None
                            r2 = requests.get(
                                "https://en.wikipedia.org/api/rest_v1/page/summary/" + content.get("href").replace(
                                    "/wiki/", ""))
                            r2_data = r2.json()
                            if r2_data and r2_data.get("extract"):
                                description = r2_data.get("extract")[:400]
                            entities.append({
                                "title": content.get("title"),
                                "href": content.get("href"),
                                "description": description
                            })
                        i = i + 1
                    out.append({
                        "heading": heading,
                        "year": year,
                        "date": d,
                        "txt": text_cleaned,
                        "entities": entities
                    })

    with open("wiki_date/{}.json".format(d), 'w') as outfile:
        json.dump(out, outfile)


class Command(BaseCommand):
    def handle(self, *args, **options):
        url = "https://en.wikipedia.org/wiki/List_of_non-standard_dates"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, features="html.parser")
        elms = soup.select("#mw-content-text > div.mw-parser-output > div.navbox > table > tbody > tr")
        start = False
        i = 0
        for elm in elms:
            if len(elm.select("th a")):
                m = elm.select("th a")[0].contents[0]
                if m == "January":
                    start = True
                if start:
                    for li in elm.select("td ul li a"):
                        d = "{} {}".format(m, li.contents[0])
                        print("{} {}".format(i, d))
                        i = i + 1
                        if i <= 199:
                            continue
                        fetch_date("https://en.wikipedia.org{}".format(li.get("href")), d)
