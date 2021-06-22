from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from django.template.defaultfilters import slugify


class Command(BaseCommand):
    def handle(self, *args, **options):
        pub = Publication.objects.get(host="9plant.com")
        plants = Post.objects.filter(primary_publication=pub, post_type="plant")
        for plant in plants:
            slug = slugify(plant.title).replace("-", "")
            term = Term.objects.filter(slug=slug).first()
            if term is None:
                term = Term.objects.create(slug=slug, title=plant.title)
            pub_term, created = PublicationTerm.objects.get_or_create(term=term, taxonomy="tag", publication=pub)
            if pub_term not in plant.terms.all():
                plant.terms.add(pub_term)
