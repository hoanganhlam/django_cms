from django.core.management.base import BaseCommand
from utils.instagram import fetch_by_hash_tag
import time
import json
import sqlite3
from django.core.serializers.json import DjangoJSONEncoder

con = sqlite3.connect('instagram.db')
cur = con.cursor()


def plant_universe_worker(k, n, count):
    print(count)
    count = count + 1
    out = fetch_by_hash_tag(k, n)
    items = out.get("results", [])
    for item in items:
        results = cur.execute("SELECT * FROM ig_posts WHERE ig_id = '%s'" % item.get("ig_id")).fetchall()
        if len(results) == 0:
            data = json.dumps(item, cls=DjangoJSONEncoder)
            cur.execute('''INSERT INTO ig_posts VALUES (?, ?)''', (item.get("ig_id"), data))
    con.commit()
    if out.get("next_id"):
        time.sleep(2)
        plant_universe_worker(k, out.get("next_id"), count)


class Command(BaseCommand):
    def handle(self, *args, **options):
        plant_universe_worker("anthuriumcrystallinum", None, 0)
