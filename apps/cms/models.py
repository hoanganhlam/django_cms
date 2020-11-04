from django.db import models
from base.interface import BaseModel, Taxonomy
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from apps.media.models import Media
from . import default


# Create your models here.


class SearchKeyword(Taxonomy, BaseModel):
    meta = JSONField(null=True, blank=True)
    # IGNORE / QUEUE / FETCHING / FETCHED
    fetch_status = models.CharField(default="IGNORE", max_length=20)


class Term(Taxonomy):
    options = JSONField(null=True, blank=True)
    measure = JSONField(null=True, blank=True)
    suggestions = models.ManyToManyField(SearchKeyword, blank=True, related_name="term")


class SearchKeywordVolume(models.Model):
    search_keyword = models.ForeignKey(SearchKeyword, related_name="searches", on_delete=models.CASCADE)
    value = models.IntegerField(default=0)
    date_taken = models.DateTimeField()


class Publication(BaseModel, Taxonomy):
    host = models.CharField(null=True, blank=True, max_length=150)
    user = models.ForeignKey(User, related_name="publications", on_delete=models.CASCADE)
    options = JSONField(null=True, blank=True, default=default.publication_options)
    measure = JSONField(null=True, blank=True)
    medias = models.ManyToManyField(Media, related_name="publication", blank=True)


class PublicationTerm(BaseModel):
    publication = models.ForeignKey(Publication, related_name="pub_terms", on_delete=models.CASCADE)
    term = models.ForeignKey(Term, related_name="pub_terms", on_delete=models.CASCADE)
    taxonomy = models.CharField(max_length=50)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="post_term_child", null=True, blank=True)
    description = models.TextField(max_length=256, null=True, blank=True)
    options = JSONField(null=True, blank=True)
    measure = JSONField(null=True, blank=True)


class Post(BaseModel, Taxonomy):
    pid = models.IntegerField(null=True, blank=True)
    user = models.ForeignKey(User, related_name="posts", on_delete=models.SET_NULL, null=True, blank=True)
    primary_publication = models.ForeignKey(
        Publication, related_name="pp_posts", blank=True, on_delete=models.SET_NULL,
        null=True)
    publications = models.ManyToManyField(Publication, related_name="posts", blank=True)

    post_parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="post_child")
    post_related = models.ManyToManyField("self", blank=True, related_name="post_related_revert")

    content = models.TextField(null=True, blank=True)  # Use Markdown
    # DRAFT / PENDING / POSTED / DELETED
    status = models.CharField(max_length=20, default="DRAFT")
    post_type = models.CharField(max_length=20, default="BLOG")
    options = JSONField(null=True, blank=True)  # activity=1
    post_date = models.DateTimeField(null=True, blank=True)
    is_guess_post = models.BooleanField(default=False)
    show_cms = models.BooleanField(default=False)
    measure = JSONField(null=True, blank=True)
    meta = JSONField(null=True, blank=True)
    terms = models.ManyToManyField(PublicationTerm, related_name="posts", blank=True)


class Ranker(models.Model):
    term = models.ForeignKey(Term, related_name="list_ranker", on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, related_name="list_ranker", on_delete=models.CASCADE)
    value = models.IntegerField(default=101)
    date_taken = models.DateTimeField()
