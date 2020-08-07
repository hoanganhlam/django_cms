from django.db import models
from base.interface import BaseModel, Taxonomy
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from apps.media.models import Media


# Create your models here.


class Term(Taxonomy):
    options = JSONField(null=True, blank=True)
    measure = JSONField(null=True, blank=True)


class TermTaxonomy(BaseModel):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="post_terms")
    taxonomy = models.CharField(max_length=50)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="post_term_child", null=True, blank=True)
    options = JSONField(null=True, blank=True)
    measure = JSONField(null=True, blank=True)


class Publication(BaseModel, Taxonomy):
    user = models.ForeignKey(User, related_name="publications", on_delete=models.CASCADE)
    options = JSONField(null=True, blank=True)
    measure = JSONField(null=True, blank=True)
    publication_terms = models.ManyToManyField(TermTaxonomy, related_name="publications", blank=True)
    medias = models.ManyToManyField(Media, related_name="publication", blank=True)


class Post(BaseModel, Taxonomy):
    user = models.ForeignKey(User, related_name="posts", on_delete=models.CASCADE)
    primary_publication = models.ForeignKey(Publication, related_name="pp_posts", blank=True, on_delete=models.SET_NULL,
                                            null=True)
    publications = models.ManyToManyField(Publication, related_name="posts", blank=True)
    post_parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="post_child")

    content = models.TextField(null=True, blank=True)  # Use Markdown
    status = models.CharField(max_length=20, default="DRAFT")
    post_type = models.CharField(max_length=20, default="BLOG")
    options = JSONField(null=True, blank=True)
    post_date = models.DateTimeField(null=True, blank=True)

    measure = JSONField(null=True, blank=True)
    meta = JSONField(null=True, blank=True)
    post_terms = models.ManyToManyField(TermTaxonomy, related_name="posts", blank=True)
