import requests
from bs4 import BeautifulSoup


def get_description(lang, search, limit):
    url = "https://" + lang + ".wikipedia.org/w/api.php?action=opensearch&format=json&formatversion=2&namespace=0&suggest=true"
    r = requests.get(
        url,
        params={"search": search, "limit": limit},
        headers={"Content-Type": "text/html; charset=UTF-8"}
    )
    data = r.json()
    return data


def get_web_meta(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, features="html.parser")
    title = ""
    if soup.title:
        title = soup.title.string
    description = soup.find("meta", property="og:description")
    if description is None:
        description = soup.find("meta", property="description")
    if description:
        description = description.get('content')
    else:
        description = ''
    images = []
    for img in soup.findAll('img'):
        images.append(img.get('src'))
    data = {
        "title": title,
        "description": description,
        "images": images
    }
    return data


def extract_place(place):
    images = []
    if place.get("images") and place.get("images").get("entities"):
        images = place.get("images").get("entities")
    return {
        "id": place.get("entityId"),
        "name": place.get("fieldPlcName"),
        "slug": place.get("fieldPlcSlug"),
        "image": list(map(extract_lonely_image, images))
    }


def extract_lonely_image(img):
    return img.get("fieldFile").get("imgixUrl")


def print_iterator(it):
    for x in it:
        print(x)
