from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from apps.media.models import Media
from django.db.models import Count, Q


class Command(BaseCommand):
    def handle(self, *args, **options):
        for x in PublicationTerm.objects.filter(publication__id=7, term__title__startswith="/java/"):
            print(x.term.title)
            x.delete()
        return
        q = Q(
            publication__id=7,
            taxonomy="tribe",
            # related__taxonomy="tribe"
            parent__isnull=False
        ) & ~Q(count_related=1) & ~Q(related__taxonomy="phylum")
        tax_terms = PublicationTerm.objects.annotate(count_related=Count("related")).filter(q)
        for term in tax_terms:
            # for related in term.related.filter(taxonomy="family"):
            #     all_genus_related = related.related.all()
            #     for g_related in all_genus_related:
            #         if g_related not in term.related.all():
            #             term.related.add(g_related)
            # if term.options is None:
            #     term.options = {}
            # term.options["is_primary"] = True
            # term.save()

            for x in term.parent.related.all():
                if x not in term.related.all():
                    term.related.add(x)

            # if term.options is None:
            #     term.options = {}
            # term.options["is_subversion"] = True
            # term.save()

            # for related in term.related.filter(taxonomy="class"):
            #     term.parent = related
            #     term.related.remove(related)
            #     term.save()

            print(term.term.title)
