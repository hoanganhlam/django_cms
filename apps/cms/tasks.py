from celery import shared_task
from apps.cms.models import Publication, Post, Term, PublicationTerm
import feedparser
from urllib.parse import urljoin, urlparse
from utils.web_checker import get_web_meta
from unidecode import unidecode
from django.template.defaultfilters import slugify
import requests
import datetime
from django.core.cache import cache
from apps.cms import models
from utils.slug import vi_slug
from django_cms.celery import app

api_key = "AIzaSyDGJRZXgn_r9BAIzu-lH7ndQhR1sJAY78M"


def sync_keyword(file_id, access_token):
    endpoint_2 = "https://sheets.googleapis.com/v4/spreadsheets/{0}?includeGridData=true&key={1}".format(
        file_id, api_key
    )
    headers = {"Authorization": "Bearer {0}".format(access_token)}
    file_data = requests.get(endpoint_2, headers=headers).json()
    if file_data.get("sheets"):
        row_data = file_data.get("sheets")[0].get("data")[0].get("rowData")
        keys = list(map(lambda x: x.get("formattedValue", ""), row_data[2].get("values")))
        start = 3
        out = []
        while start < len(row_data):
            keyword = row_data[start].get("values")[0].get("formattedValue", None)
            checker = models.SearchKeyword.objects.filter(slug=vi_slug(keyword)).first()
            if checker is None or checker.searches.count() == 0:
                if checker is None:
                    checker = models.SearchKeyword.objects.create(title=keyword)
                new_record = {
                    "records": []
                }
                meta = {}
                for i, val in enumerate(row_data[start].get("values")):
                    if keys[i] == "Keyword" and val.get("formattedValue", None) is not None:
                        new_record["title"] = val.get("formattedValue", None)
                    if keys[i] == "Top of page bid (low range)" and val.get("formattedValue", None) is not None:
                        meta["bid_low"] = val.get("formattedValue", None)
                        new_record["bid_low"] = val.get("formattedValue", None)
                    if keys[i] == "Top of page bid (high range)" and val.get("formattedValue",
                                                                             None) is not None:
                        meta["bid_high"] = val.get("formattedValue", None)
                        new_record["bid_high"] = val.get("formattedValue", None)
                    if "Searches: " in keys[i]:
                        date_str = keys[i].replace("Searches: ", "")
                        date_obj = datetime.datetime.strptime(date_str, '%b %Y')

                        models.SearchKeywordVolume.objects.create(
                            search_keyword=checker,
                            value=val.get("formattedValue", None),
                            date_taken=date_obj
                        )
                        new_record["records"].append({
                            "date": date_obj,
                            "value": val.get("formattedValue", None)
                        })
                checker.meta = meta
                checker.fetch_status = "fetched"
                checker.save()
                out.append(new_record)
            start += 1


def get_new_token(refresh_token):
    uri = "https://oauth2.googleapis.com/token"
    re = requests.post(
        url=uri,
        params={
            'client_id': "645295726451-p962g9janknllps6qnduft3birhddupp.apps.googleusercontent.com",
            "client_secret": "gmT2Pk2EKbuiwvKXHqcyJEJI",
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        },
        headers={'content-type': 'application/x-www-form-urlencoded'}
    ).json()
    return re.get("access_token")


@shared_task
def add():
    publications = Publication.objects.filter(options__feeds__isnull=False)
    for pub in publications:
        if len(pub.options.get("feeds")):
            for feed in pub.options.get("feeds"):
                x = feedparser.parse(feed)
                for entry in x.get("entries"):
                    # 'title', 'title_detail', 'links', 'link', 'id', 'guidislink',
                    # 'tags', 'authors', 'author', 'author_detail', 'published',
                    # 'published_parsed', 'updated', 'updated_parsed', 'content', 'summary'
                    url_parsed = urljoin(entry.get("link"), urlparse(entry.get("link")).path)
                    check = Post.objects.filter(post_type="link", meta__url=url_parsed, db_status=1).first()
                    if check is None:
                        meta = get_web_meta(url_parsed)
                        if meta:
                            new_post = Post.objects.create(
                                title=entry.get("title"),
                                description=meta.get("description"),
                                meta={
                                    "url": url_parsed,
                                    "authors": entry.get("authors"),
                                    "published": entry.get("published")
                                },
                                post_type="link",
                                status="POSTED",
                                show_cms=True,
                                is_guess_post=True
                            )
                            new_post.publications.add(pub)
                            if entry.get("tags"):
                                for tag in entry.get("tags"):
                                    slug = slugify(unidecode(tag.get("term")))
                                    term, created = Term.objects.get_or_create(
                                        slug=slug,
                                        defaults={"title": tag.get("term")}
                                    )
                                    pub_term, created = PublicationTerm.objects.get_or_create(
                                        publication=pub,
                                        taxonomy="tag",
                                        term=term
                                    )
                                    new_post.terms.add(pub_term)


@shared_task
def test():
    print("OK")


@app.task(bind=True)
def task_sync_drive(self, *args, **kwargs):
    print(kwargs)
    if "google_access_token" in cache:
        access_token = cache.get("google_access_token")
    else:
        access_token = "ya29.A0AfH6SMBVPLVY7XVbn01pqsBcpeinoYu-0y6PvKGkim0xKUOwbJSyOL_YetvUCSRAqBoXTROZz_j3MmeDxfbExrdxLxyX7dFKMtwhoEX-NNXA9J-vyeust9zB_pHMZrMdGJVs21lIBXwZzl66C4h1VUysaBsRwNuZ_mOWhADzC3g"
    refresh_token = "1//0etLWfot9rSUYCgYIARAAGA4SNwF-L9IrhmHI5zYQf1kzDzeccSzOhMU11e0126JlXnkkGE15EysbnP5VBVZA8ZTDMl9F6zhyAeo"
    endpoint = "https://www.googleapis.com/drive/v3/files?q=name%3D%22{0}%22&key={1}".format(kwargs.get("file_name"),
                                                                                             api_key)
    headers = {"Authorization": "Bearer {0}".format(access_token)}
    re = requests.get(endpoint, headers=headers)
    if re.status_code == 401:
        access_token = get_new_token(refresh_token)
        cache.set("google_access_token", access_token, 60 * 60 * 24 * 365)
        headers = {"Authorization": "Bearer {0}".format(access_token)}
        re = requests.get(endpoint, headers=headers)
    if re.status_code == 200:
        data = re.json()
        if data.get("files") and len(data.get("files")) > 0:
            the_file = data.get("files")[0]
            sync_keyword(the_file.get("id"), access_token)
