import requests
from bs4 import BeautifulSoup


def test():
    url = "https://www.thesill.com/collections/live-plants"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, features="html.parser")
    elms = soup.select(".product-card")
    for elm in elms:
        print(elm.find("a").get("href"))
        print(elm.find("h3").find(text=True).replace("\n", ""))
