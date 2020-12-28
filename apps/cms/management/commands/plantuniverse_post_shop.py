from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from django.template.defaultfilters import slugify


class Command(BaseCommand):
    def handle(self, *args, **options):
        pub = Publication.objects.get(host="plantuniverse.co")
        shop_keywords = [
            "plant shopping", "plant shop", "sale", "plant sale", "houseplants for sale", "plant discount",
            "plants on sale", "plant offer", "plants for sale", "for sale", "indoor plants for sale"
        ]
        term, is_created = Term.objects.get_or_create(slug="forsale")
        pub_term, created = PublicationTerm.objects.get_or_create(term=term, publication=pub, taxonomy="tag")
        shop_tags = list(map(lambda x: x.replace(" ", ""), shop_keywords)) + list(
            map(lambda x: x.replace(" ", "_"), shop_keywords))
        posts = Post.objects.filter(primary_publication=pub, post_type="post", terms__term__slug__in=shop_tags)
        for p in posts:
            if pub_term not in p.terms.all():
                p.terms.add(pub_term)
                print("A")
            else:
                print("B")
