from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from apps.cms.models import Post, Publication, Term, TermTaxonomy
from django.contrib.auth.models import User
from django.db.models import Q
user = User.objects.get(pk=1)
pub = Publication.objects.get(pk=4)


class Command(BaseCommand):

    def handle(self, *args, **options):
        queryset = Post.objects.filter(~Q(publications__id=3))
        for post in queryset:
            if str(post.id) not in post.slug:
                post.slug = post.slug + '-' + str(post.id)
                post.save()
                print(post.id)
