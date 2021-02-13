from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion, crawl_retriever, crawl_retriever_link
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from django.template.defaultfilters import slugify

publication = Publication.objects.get(pk=4)


class Command(BaseCommand):
    def handle(self, *args, **options):
        for url in crawl_retriever_link():
            out = crawl_retriever(url)
            for raw_data in out:
                fact_instance = Post.objects.filter(meta__frid=raw_data.get("id")).first()
                if fact_instance is None:
                    fact_instance = Post.objects.create(
                        title=raw_data.get("content").split(".")[0][:160],
                        description=raw_data.get("content") if len(raw_data.get("content")) < 500 else None,
                        content=raw_data.get("content") if len(raw_data.get("content")) > 500 else None,
                        meta={
                            "frid": raw_data.get("id"),
                            "refers": raw_data.get("refers")
                        },
                        status="POSTED",
                        primary_publication=publication,
                        show_cms=True,
                        post_type="post"
                    )
                for tag in raw_data.get("tags"):
                    term, is_created = Term.objects.get_or_create(slug=slugify(tag), defaults={
                        "title": tag
                    })
                    pub_term, is_created = PublicationTerm.objects.get_or_create(
                        publication=publication,
                        term=term,
                        taxonomy="tag"
                    )
                    all_pub_term = fact_instance.terms.all()
                    if pub_term not in all_pub_term:
                        fact_instance.terms.add(pub_term)
                    if tag == raw_data.get("title"):
                        fact_instance.options = {
                            "done_tasks": [],
                            "primary_term": pub_term.id
                        }
                        fact_instance.save()
                print(fact_instance.id)
