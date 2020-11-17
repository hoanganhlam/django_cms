from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword
from utils.web_checker import get_keyword_suggestion
import requests


class Command(BaseCommand):
    def handle(self, *args, **options):
        # terms = Term.objects.filter(suggestions__isnull=True, pub_terms__publication__id=7)
        # for term in terms:
        #     old = term.suggestions.all()
        #     suggestions = get_keyword_suggestion(term.title)
        #     print(term)
        #     if len(old) == 0 and len(suggestions) > 0:
        #         for s in suggestions:
        #             kw, created = SearchKeyword.objects.get_or_create(title=s)
        #             print(kw)
        #             if kw not in old:
        #                 term.suggestions.add(kw)

        # posts = Post.objects.filter(primary_publication__id=7, id__gte=10629, post_type="post")
        # plant = Post.objects.get(pk=10579)
        # print(plant)
        # for post in posts:
        #     if post.post_related.filter(post_type="plant").count() == 0:
        #         post.post_related.add(plant)
        #         print(post.id)
        # if post.options and post.meta and post.meta.get("media") is None:
        #     post.meta['media'] = post.options.get("media")
        #     post.save()
        #     print(post.id)

        posts = Post.objects.filter(primary_publication__id=5, post_type="post")
        for post in posts:
            post.show_cms = True
            post.save()
