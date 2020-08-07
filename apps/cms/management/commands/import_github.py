from django.core.management.base import BaseCommand
from apps.repository.models import Repository, Taxonomy, GitUser
from utils.slug import _slug_strip, vi_slug
from apps.repository.management.commands.fetcher import fetch_github, fetch_npm, fetch_open_base
import requests
from datetime import datetime, timedelta


def save_data(obj, score, search):
    # Check user
    username = obj.get("publisher").get("username")
    email = obj.get("publisher").get("email")
    name = obj.get("author").get("name") if obj.get("author") else None
    git_user = GitUser.objects.filter(username=username).first()
    if git_user is None:
        git_user = GitUser(username=username, email=email, full_name=name)
        git_user.save()

    # Repository
    repo = Repository.objects.filter(name=obj.get("name")).first()
    if repo is None:
        last = Repository.objects.order_by('-id').first()
        last_time = last.date_published + timedelta(hours=0.07)
        repo = Repository(
            name=obj.get("name"),
            description=obj.get("description"),
            author=git_user,
            id_github=obj.get("links").get("repository"),
            id_npm=obj.get("links").get("npm"),
            score=score,
            date_published=last_time
        )
        repo.save()
        print(repo.id)
        print(last_time)
        # Check Taxonomy
        check_search = Taxonomy.objects.filter(slug=vi_slug(_slug_strip(search))).first()
        if check_search is None:
            check_search = Taxonomy(
                name=search,
                slug=vi_slug(_slug_strip(search)),
                parent_id=221,
                flags=['component'],
                visible=True)
            check_search.save()
        repo.taxonomies.add(check_search)
        if obj.get("keywords"):
            for kw in obj.get("keywords"):
                slug = vi_slug(_slug_strip(kw))
                taxonomy = Taxonomy.objects.filter(slug=slug).first()
                if taxonomy is None:
                    taxonomy = Taxonomy(name=kw, slug=slug)
                    taxonomy.save()
                    repo.taxonomies.add(taxonomy)
        if repo.id_github is not None or repo.id_github != "":
            fetch_npm(repo)
            fetch_github(repo)
        if repo.id_github is not None and repo.contributes.all().count() == 0:
            fetch_open_base(repo)


def fetch_data(f, search):
    headers = {'origin': 'x-requested-with'}
    uri = "https://cors-anywhere.herokuapp.com/https://api.npms.io/v2/search"
    params = {
        "q": search,
        # "page": 1,
        # "topic": "vuejs",
        "size": 10,
        "from": f
    }
    r = requests.get(
        uri,
        params=params,
        headers=headers
    )
    if r.status_code == 200:
        data = r.json()
        items = [] if data is None else data.get("results")
        for item in items:
            save_data(item.get("package"), item.get("score"), search)
        if data.get("total") > f + 10:
            fetch_data(f + 10, search)


class Command(BaseCommand):
    def handle(self, *args, **options):
        arr = [
            "Overlay",
            "Parallax",
            "Icons",
            "Marquee",
            "Menu",
            "Carousel",
            "Charts",
            "Time",
            "Calendar",
            "Map",
            "Audio",
            "Video",
            "Infinite Scroll",
            "Pull-to-refresh",
            "Markdown",
            "PDF",
            "Tree",
            "Graph",
            "Social Sharing",
            "QR Code",
            "Search",
            "Miscellaneous",
            "Avatar",
            "Heatmap",
            "Tabs",
            "Map",
            "Form",
            "Select",
            "Datetime Picker",
            "Slider",
            "Drag and Drop",
            "Autocomplete",
            "Type Select",
            "Color Picker",
            "Switch",
            "Masked Input",
            "Rich Text Editing",
            "Upload",
            "Menu",
            "CSV",
            "Canvas"
        ]
        for x in arr:
            fetch_data(0, "Vue " + x)
