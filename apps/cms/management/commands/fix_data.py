from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.cms.models import Post, Publication, PublicationTerm
from apps.media.models import Media
from apps.media.api.serializers import MediaSerializer


class Command(BaseCommand):
    def handle(self, *args, **options):
        posts = Post.objects.all()
        for post in posts:
            old_terms = post.post_terms.all()
            for old_term in old_terms:
                new_term = PublicationTerm.objects.filter(
                    term=old_term.term,
                    publication=post.primary_publication,
                    taxonomy=old_term.taxonomy).first()
                if new_term is None:
                    new_term = PublicationTerm.objects.create(
                        term=old_term.term,
                        publication=post.primary_publication,
                        taxonomy=old_term.taxonomy
                    )
                post.terms.add(new_term)
            print(post.id)
