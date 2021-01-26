import requests
from bs4 import BeautifulSoup
import re


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


def get_keyword_suggestion(keyword):
    out = []
    qs = ["What", "can", "when", "how", "Which", "why", "will", "who", "whe", "are"]
    for q in qs:
        url = "http://suggestqueries.google.com/complete/search"
        r = requests.get(
            url,
            params={"q": q + " " + keyword, "output": "toolbar", "hl": "en"},
            headers={"Content-Type": "text/html; charset=UTF-8"}
        )
        soup = BeautifulSoup(r.content, 'xml')
        for x in soup.find_all('suggestion'):
            out.append(x.get("data"))
    return out


def crawl_retriever_link():
    r = requests.get("https://www.factretriever.com/hashtags/kidfriendly")
    soup = BeautifulSoup(r.content, features="html.parser")
    elms = soup.select(".tagArticle a")
    return list(map(lambda a: "https://www.factretriever.com" + a.get("href"), elms))


def crawl_retriever(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, features="html.parser")
    preferences = {}
    tags = []
    output = []
    # get questions
    # for elm in soup.select("#ddivFrequentlyAskedQuestion .divQuestionsAnswer"):
    #     print(elm)

    # Instance name
    elms = soup.select(".customBreadcrumb li")
    title = elms[len(elms) - 1].find_all(text=True)[0].replace(" Facts", "")
    if "Top 10" in title:
        return []
    tags.append(title)
    # get tags
    for elm in soup.select("#ContentPlaceHolder1_divInnerHashTag a"):
        tags.append(re.sub(r"(\w)([A-Z])", r"\1 \2", elm.text.replace("#", "")))
    # Get references
    for elm in soup.select(".divReferences .pReference"):
        sup = str(elm.contents[0].find_all(text=True))
        elm.contents[0].decompose()
        preferences[re.search(r"\[([A-Za-z0-9_]+)\]", sup.replace("'", "")).group(1)] = str(elm.decode_contents())
    # Get items
    for elm in soup.select(".factsList li"):
        keys = []
        for sup in elm.select("sub"):
            keys = keys + re.findall(r"\[([A-Za-z0-9_]+)\]", str(sup).replace("'", ""))
        for x in elm.find_all('sub'):
            x.decompose()
        output.append({
            "id": elm.get("id"),
            "title": title,
            "tags": tags,
            "content": "".join(elm.find_all(text=True)),
            "refers": list(map(lambda a: preferences.get(a), keys))
        })
    return output
