from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion, crawl_retriever, crawl_retriever_link
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from django.template.defaultfilters import slugify
from django.db.models import Q
from django.db.models import OuterRef, Subquery, Count, Min

publication = Publication.objects.get(pk=4)


class Command(BaseCommand):
    def handle(self, *args, **options):
        posts = Post.objects.filter(primary_publication=publication).order_by("measure__score").distinct()
        print(posts.count())