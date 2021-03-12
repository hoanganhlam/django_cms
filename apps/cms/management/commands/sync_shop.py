from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from apps.media.models import Media
from django.contrib.auth.models import User
from utils.sync_shop import test
from utils.instagram import fetch_by_hash_tag, fetch_user, fetch_avatar
import json
import random
from instagram_web_api import Client, ClientCompatPatch, ClientError, ClientLoginError

pub = Publication.objects.get(pk=7)


def convert_ig_to_store(user_id):
    user = User.objects.filter(profile__options__source="instagram", profile__options__id=user_id).first()
    user_raw = None
    if user is None:
        user_raw = fetch_user(user_id)
        user = User.objects.filter(username=user_raw.get("username"), profile__options__source="instagram").first()
        if user is None:
            user = User.objects.create(
                username=user_raw.get("username")
            )
            media = None
            if user_raw.get("profile_pic_id"):
                media = Media.objects.save_url(user_raw.get("hd_profile_pic_url_info").get("url"))
            profile = user.profile
            profile.nick = user_raw.get("full_name")
            profile.options = {"source": "instagram", "id": user_raw.get("id")}
            profile.media = media
            profile.save()
    store = Post.objects.filter(meta__ig_id=user_id, primary_publication=pub).first()
    if store is None:
        if user_raw is None:
            user_raw = fetch_user(user_id)
        store = Post.objects.create(
            title=user_raw.get("username"),
            description=user_raw.get("biography"),
            user=user,
            primary_publication=pub,
            post_type="store",
            status="POSTED",
            show_cms=True,
            meta={
                "ig_id": user_id,
                "source": "instagram",
                "media": user.profile.media_id if user.profile.media else None,
                "ig_username": user_raw.get("username")
            }
        )
        if user.profile.media is not None:
            store.meta["media"] = user.profile.media_id
        elif user_raw.get("profile_pic_id"):
            try:
                media = Media.objects.save_url(user_raw.get("hd_profile_pic_url_info").get("url"))
                store.media["media"] = media.id
            except Exception as e:
                print(user_raw.get("profile_pic_id"))
                print(e)

    if user.profile.media is None or store.meta['media'] is None:
        media = Media.objects.save_url(user_raw.get("hd_profile_pic_url_info").get("url"))
        store.meta["media"] = media.id
        user.profile.media = media
    store.save()
    print(store.title)
    return user, store


def fetch_all(hash_tag, key):
    out = fetch_by_hash_tag(hash_tag, key)
    for result in out.get("results", []):
        user, store = convert_ig_to_store(result.get("user").get("ig_id"))
        medias = []
        for img in result.get("images", []):
            media = Media.objects.save_url(img, user=user)
            medias.append(media.id)
        new_post = Post.objects.create(
            title="Post by " + result.get("user").get("full_name") if result.get("user").get(
                "full_name") else result.get("user").get("username"),
            description=result.get("caption")[:300] if result.get("caption") else None,
            meta={
                "ig_id": result.get("ig_id"),
                "credit": result.get("user").get("username"),
                "medias": medias
            },
            primary_publication=pub,
            user=user,
            post_type="post",
            show_cms=True,
            status="POSTED"
        )
        new_post.post_related.add(store)
        for tag in result.get("tags", []):
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
                except Exception as e:
                    pass
    if out.get("next_id"):
        fetch_all(hash_tag, out.get("next_id"))


class Command(BaseCommand):
    def handle(self, *args, **options):
        fetch_all("plantshop", None)
