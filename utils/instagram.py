from utils.slug import _slug_strip, vi_slug
from datetime import datetime
import json
import codecs
import os.path
import logging
import argparse

try:
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)
except ImportError:
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def on_login_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print('SAVED: {0!s}'.format(new_settings_file))


user_name = 'hoanglamyeah'
password = 'Lamhoang.bk59'
settings_file = "test_credentials.json"
device_id = None
try:
    if not os.path.isfile(settings_file):
        print('Unable to find file: {0!s}'.format(settings_file))
        api = Client(
            user_name, password,
            on_login=lambda x: on_login_callback(x, settings_file))
    else:
        with open(settings_file) as file_data:
            cached_settings = json.load(file_data, object_hook=from_json)
        print('Reusing settings: {0!s}'.format(settings_file))
        device_id = cached_settings.get('device_id')
        # reuse auth settings
        api = Client(
            user_name, password,
            settings=cached_settings)
except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
    api = Client(
        user_name, password,
        device_id=device_id,
        on_login=lambda x: on_login_callback(x, settings_file))
except ClientLoginError as e:
    print('ClientLoginError {0!s}'.format(e))
except ClientError as e:
    print('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response))
except Exception as e:
    print('Unexpected Exception: {0!s}'.format(e))


def fetch_by_hash_tag(search, max_id=None):
    # Start
    keyword = _slug_strip(vi_slug(search), separator="")
    if max_id:
        results = api.feed_tag(keyword, rank_token="08276948-21a8-11ea-8c58-acde48001122", max_id=max_id)
    else:
        results = api.feed_tag(keyword, rank_token="08276948-21a8-11ea-8c58-acde48001122")
    next_max_id = results.get('next_max_id')
    arr = results.get("items")
    out_results = list(map(extract_item, arr))
    return {
        "next_id": next_max_id,
        "results": out_results
    }


def fetch_users(search, max_id=None):
    user_name = 'lam.laca'
    password = 'Hoanganhlam@no99'
    api = Client(user_name, password)
    if max_id:
        results = api.search_users(search, max_id=max_id)
    else:
        results = api.search_users(search)
    return results


def extract_item(item):
    location = None
    if item.get("lat") is not None and item.get("lng") is not None:
        location = {
            "lat": item.get("lat"),
            "lng": item.get("lng")
        }
    caption = None if item.get("caption") is None else item.get("caption").get("text")
    user_raw = item.get("user")
    images = []
    if item.get("image_versions2") or item.get("image"):
        images = [extract_media(item)]
    if item.get("carousel_media"):
        x = item.get("carousel_media")
        images = list(map(extract_media, x))

    user = {
        "ig_id": user_raw.get("pk"),
        "full_name": user_raw.get("full_name"),
        "username": user_raw.get("username"),
        "profile_pic_id": user_raw.get("profile_pic_id")
    }
    tags = []
    if caption:
        tags = [word.replace('#', '') for word in caption.split() if word.startswith('#')]
    return {
        "ig_id": item.get("pk"),
        "tags": tags,
        "user": user,
        "caption": caption,
        "coordinate": location,
        "time_posted": datetime.fromtimestamp(item.get("taken_at")),
        "images": images,
        "comment_count": item.get("comment_count"),
        "profile_pic_id": item.get("profile_pic_id")
    }


def extract_media(item):
    image = None
    if item.get("image_versions2"):
        image = item.get("image_versions2").get("candidates")[0].get("url")
    if item.get("image"):
        image = item.get("image").get("candidates")[0].get("url")
    return image


def get_comment(item_id):
    return api.media_comments(item_id)


def fetch_avatar(item_id):
    if item_id is None:
        return None
    test = api.media_info(item_id)
    if test and len(test.get("items", [])) > 0:
        return extract_media(test.get("items")[0])
    return None


def fetch_user(user_id):
    return api.user_info(user_id).get("user")
