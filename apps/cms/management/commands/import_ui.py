from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, Term, TermTaxonomy
from apps.media.models import Media
from django.contrib.auth.models import User
import requests

user = User.objects.get(pk=1)
pub = Publication.objects.get(pk=5)


def fetch_data(page):
    headers = {'origin': 'x-requested-with'}
    uri = "https://api.uihunt.com/v1/public/uis"
    params = {
        "page_size": 25,
        "page": page
    }
    r = requests.get(
        uri,
        params=params,
        headers=headers
    )
    if r.status_code == 200:
        data = r.json()
        items = [] if data is None else data.get("results")
        for item in items:
            test = Post.objects.filter(pid=item.get("id")).first()
            description = item.get("short_description")
            if description and len(description) > 500:
                description = description[:499]
            if test is None:
                meta = item.get("options")
                post = Post.objects.create(
                    pid=item.get("id"),
                    title=item.get("title"),
                    user=user,
                    description=description,
                    content=item.get("description"),
                    post_type="post",
                    meta=meta,
                    options={
                        "medias": [],
                        "user": item.get("user").get("username")
                    },
                    primary_publication=pub
                )
                if item.get("hash_tags"):
                    for tax in item.get("hash_tags"):
                        term_tax = TermTaxonomy.objects.filter(taxonomy="tag", term__title=tax.get("title")).first()
                        if term_tax is None:
                            term = Term.objects.filter(title=tax.get("title")).first()
                            if term is None:
                                term = Term.objects.create(title=tax.get("title"))
                            term_tax = TermTaxonomy.objects.create(taxonomy="tag", term=term)
                        post.post_terms.add(term_tax)
                if item.get("medias"):
                    for media_raw in item.get("medias"):
                        media = Media.objects.save_url(media_raw.get("sizes").get("full_size"))
                        if media is not None:
                            pub.medias.add(media)
                            post.options["medias"].append(media.id)
                post.publications.add(pub)
                post.save()
                print(post.id)
        if len(items) > 0:
            fetch_data(page + 1)


class Command(BaseCommand):
    def handle(self, *args, **options):
        fetch_data(1)
