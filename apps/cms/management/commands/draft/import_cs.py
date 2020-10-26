from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, Term, TermTaxonomy
from apps.media.models import Media
from django.contrib.auth.models import User
import requests

user = User.objects.get(pk=1)
pub = Publication.objects.get(pk=3)


class Command(BaseCommand):
    def handle(self, *args, **options):
        headers = {'origin': 'x-requested-with'}
        uri = "https://api.cheatsheetmaker.com/v1/sheet/cheat-sheets/?format=json&all=true"
        r = requests.get(
            uri,
            headers=headers
        )
        if r.status_code == 200:
            data = r.json()
            items = [] if data is None else data
            for item in items:
                test = Post.objects.filter(title=item.get("title")).first()
                if test is None:
                    post = Post.objects.create(
                        title=item.get("title"),
                        user=user,
                        description=item.get("description"),
                        post_type="cheat-sheet",
                        primary_publication=pub,
                        meta={
                            "sheets": item.get("sheets")
                        },
                        status="DRAFT" if item.get("media") is None else "POSTED"
                    )
                    for tax in item.get("taxonomies"):
                        term_tax = TermTaxonomy.objects.filter(taxonomy="tag", term__title=tax.get("title")).first()
                        if term_tax is None:
                            term = Term.objects.filter(title=tax.get("name")).first()
                            if term is None:
                                term = Term.objects.create(title=tax.get("title"))
                            term_tax = TermTaxonomy.objects.create(taxonomy="tag", term=term)
                        post.post_terms.add(term_tax)
                    post.publications.add(pub)
                    if item.get("media") is not None:
                        media = Media.objects.save_url(item.get("media").get("sizes").get("fullsize"))
                        if media is not None:
                            pub.medias.add(media)
                            post.options = {"media": media.id}
                    post.save()
                    print(post.id)
