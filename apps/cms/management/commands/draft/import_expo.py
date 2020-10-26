from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, Term, TermTaxonomy
from django.contrib.auth.models import User
import requests

user = User.objects.get(pk=1)
pub = Publication.objects.get(pk=1)


def fetch_data(page):
    headers = {'origin': 'x-requested-with'}
    uri = "https://expo.bubblask.com/public/repository/repositories/"
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
            test = Post.objects.filter(title=item.get("name")).first()
            if test is None:
                post = Post.objects.create(
                    id=item.get("id"),
                    title=item.get("name"),
                    user=user,
                    description=item.get("description"),
                    post_type="REPO",
                    meta={
                        "data_github": item.get("data_github"),
                        "data_npm": item.get("data_npm"),
                        "score": item.get("score")
                    }
                )
                for tax in item.get("taxonomies"):
                    term_tax = TermTaxonomy.objects.filter(taxonomy="tag", term__title=tax.get("name")).first()
                    if term_tax is None:
                        term = Term.objects.filter(title=tax.get("name")).first()
                        if term is None:
                            term = Term.objects.create(title=tax.get("name"))
                        term_tax = TermTaxonomy.objects.create(taxonomy="tag", term=term)
                    post.post_terms.add(term_tax)
                post.publications.add(pub)
                post.save()
                print(post.id)
        if len(items) > 0:
            fetch_data(page + 1)


def fetch_x(i):
    headers = {'origin': 'x-requested-with'}
    uri = "https://expo.bubblask.com/public/repository/repositories/" + str(i) + "/"
    r = requests.get(uri, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        return None


class Command(BaseCommand):
    def handle(self, *args, **options):
        # fetch_data(1)
        queryset = TermTaxonomy.objects.filter(term__title__contains="vue")
        for term in queryset:
            pub.publication_terms.add(term)
