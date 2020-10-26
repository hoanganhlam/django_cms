from celery import shared_task
from apps.cms.models import Publication, Post, Term, PublicationTerm
import feedparser
from urllib.parse import urljoin, urlparse
from utils.web_checker import get_web_meta
from unidecode import unidecode
from django.template.defaultfilters import slugify


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
