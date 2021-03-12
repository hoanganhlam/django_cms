from django.db import models
from apps.media.models import Media
from base.interface import BaseModel, Taxonomy
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
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


class Theme(BaseModel, Taxonomy):
    options = JSONField(null=True, blank=True, default=default.theme_options)
    media = models.ForeignKey(Media, related_name="themes", blank=True, null=True, on_delete=models.SET_NULL)
    price = models.FloatField(default=0)
    status = models.CharField(default="developing", max_length=500)
    user = models.ForeignKey(User, related_name="themes", on_delete=models.CASCADE)


class Publication(BaseModel, Taxonomy):
    host = models.CharField(null=True, blank=True, max_length=150)
    user = models.ForeignKey(User, related_name="publications", on_delete=models.CASCADE)
    options = JSONField(null=True, blank=True, default=default.publication_options)
    measure = JSONField(null=True, blank=True)
    medias = models.ManyToManyField(Media, related_name="publication", blank=True)
    terms = models.ManyToManyField(Term, related_name="publication", blank=True)

    def draw_calendar_post(self):
        posts = list(self.posts.all()) + list(self.pp_posts.all())
        if self.measure is None:
            self.measure = {"cal_post": {}}
        if self.measure.get("cal_post") is None:
            self.measure["cal_post"] = {}
        for post in posts:
            k = "{}-{}-{}".format(post.created.year, post.created.month, post.created.day)
            if k not in self.measure["cal_post"]:
                self.measure["cal_post"][k] = 1
            else:
                self.measure["cal_post"][k] = self.measure["cal_post"][k] + 1
        self.save()


class PublicationCooperation(BaseModel):
    publication = models.ForeignKey(Publication, related_name="pub_cooperation_from", on_delete=models.CASCADE)
    cooperation = models.ForeignKey(Publication, related_name="pub_cooperation_to", on_delete=models.CASCADE)
    status = models.CharField(default="pending", max_length=50)
    user = models.ForeignKey(User, related_name="pub_cooperation", on_delete=models.CASCADE)
    options = JSONField(null=True, blank=True, default=default.publication_cooperation_options)


class PublicationUser(BaseModel):
    publication = models.ForeignKey(Publication, related_name="publication_user", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="publication_user", on_delete=models.CASCADE)
    status = models.CharField(default="pending", max_length=50)
    options = JSONField(null=True, blank=True, default=default.publication_options)


class PublicationTheme(models.Model):
    theme = models.ForeignKey(Theme, related_name="publication_themes", on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, related_name="publication_themes", on_delete=models.CASCADE)
    options = JSONField(null=True, blank=True, default=default.theme_options)
    is_active = models.BooleanField(default=False)


class PublicationTerm(BaseModel):
    publication = models.ForeignKey(Publication, related_name="pub_terms", on_delete=models.CASCADE)
    term = models.ForeignKey(Term, related_name="pub_terms", on_delete=models.CASCADE)
    taxonomy = models.CharField(max_length=50)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="post_term_child", null=True, blank=True)
    related = models.ManyToManyField("self", related_name="related_reverse", blank=True, symmetrical=False)
    description = models.TextField(max_length=256, null=True, blank=True)
    media = models.ForeignKey(Media, related_name="publication_terms", blank=True, null=True, on_delete=models.SET_NULL)
    options = JSONField(null=True, blank=True)
    measure = JSONField(null=True, blank=True)
    meta = JSONField(null=True, blank=True)
    show_cms = models.BooleanField(default=False)

    def children(self):
        out = []
        if self.post_term_child.all().count() > 0:
            children = self.post_term_child.all()
            out = out + list(children.values_list("id", flat=True))
            for child in children:
                out = out + child.children()
        return out

    def parents(self):
        out = []
        if self.parent:
            out.append(self.parent.id)
            out = out + list(self.parent.parents())
        return out

    def entities(self):
        return self.children() + self.parents()

    def sync(self):
        posts = self.posts.all()
        same_related = self.related.filter(taxonomy=self.taxonomy)
        if same_related.count() > 0:
            for post in posts:
                post_terms = post.terms.all()
                for related in same_related:
                    if related not in post_terms:
                        post.terms.add(related)


class Post(BaseModel, Taxonomy):
    pid = models.IntegerField(null=True, blank=True)
    user = models.ForeignKey(User, related_name="posts", on_delete=models.SET_NULL, null=True, blank=True)
    primary_publication = models.ForeignKey(Publication, related_name="pp_posts", blank=True, on_delete=models.SET_NULL,
                                            null=True)
    publications = models.ManyToManyField(Publication, related_name="posts", blank=True)
    collaborators = models.ManyToManyField(User, related_name="collaborated_posts", blank=True)
    post_parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="post_child")
    post_related = models.ManyToManyField("self", blank=True, related_name="post_related_revert", symmetrical=False)

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


class Contribute(BaseModel):
    user = models.ForeignKey(User, related_name="contributes", on_delete=models.CASCADE)
    target_content_type = models.ForeignKey(
        ContentType, related_name='contribute_target',
        on_delete=models.CASCADE, db_index=True
    )
    target_object_id = models.CharField(max_length=255, db_index=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')
    field = models.CharField(max_length=120)
    # type - Media, Post, Term, str, int, list
    # data -
    value = JSONField(null=True, blank=True)
    # draft / pending / accept / deleted
    status = models.CharField(max_length=20, default="draft")
