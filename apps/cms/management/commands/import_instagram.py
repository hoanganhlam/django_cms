from django.core.management.base import BaseCommand
import json
import sqlite3
from apps.media.models import Media
from apps.cms.models import Post, Publication, Term, PublicationTerm
from apps.authentication.models import Profile
from django.contrib.auth.models import User

con = sqlite3.connect('instagram.db')
cur = con.cursor()


def sync_ig_user(user_raw):
    if user_raw is None:
        return None
    test_user, created = User.objects.get_or_create(username=user_raw.get("username"))
    user = test_user
    if created:
        test_profile, is_created = Profile.objects.get_or_create(
            user=user,
            defaults={
                "nick": user_raw.get("full_name"),
                "options": {"source": "instagram", "id": user_raw.get("id")},
                "media": None
            }
        )
        if test_profile.media is None and not is_created:
            if test_profile.media is None:
                test_profile.nick = user_raw.get("full_name")
                test_profile.options = {"source": "instagram", "id": user_raw.get("id")}
                test_profile.media = None
                test_profile.save()
    return user


class Command(BaseCommand):
    def handle(self, *args, **options):
        pub = Publication.objects.get(pk=31)
        admin = User.objects.get(pk=1)
        results = cur.execute("SELECT * FROM ig_posts WHERE tags LIKE '%monsteradeliciosavariegata%'").fetchall()
        for r in results:
            pk = r[0]
            item = json.loads(r[1])
            instance = Post.objects.filter(meta__ig_id=pk).first()
            if instance is None and len(item.get("images", [])) > 0:
                user = sync_ig_user(item.get("user"))
                medias = []
                for img in item.get("images", []):
                    media = Media.objects.save_url(img)
                    medias.append(media.id)
                meta = {
                    "ig_id": pk,
                    "credit": item.get("user").get("username"),
                    "medias": medias
                }
                new_post = Post.objects.create(
                    title="Post by " + item.get("user").get("full_name") if item.get("user").get(
                        "full_name") else item.get("user").get("username"),
                    description=item.get("caption")[:300] if item.get("caption") else None,
                    meta=meta,
                    primary_publication=pub,
                    user=user if user is not None else admin,
                    post_type="post",
                    show_cms=True,
                    status="POSTED"
                )
                for tag in item.get("tags", []):
                    if len(tag) < 100:
                        try:
                            term, is_created = Term.objects.get_or_create(slug=tag, defaults={
                                "title": tag
                            })
                            pub_term, is_created = PublicationTerm.objects.get_or_create(
                                publication=pub, term=term,
                                defaults={
                                    "taxonomy": "tag"
                                })
                            new_post.terms.add(pub_term)
                            plants = Post.objects.filter(
                                terms__taxonomy="tag",
                                terms__term__slug=tag,
                                post_type="plant",
                                primary_publication=pub
                            )
                            for plant in plants:
                                new_post.post_related.add(plant)
                        except Exception as e:
                            print(e)
                            pass
                print(new_post.id)
