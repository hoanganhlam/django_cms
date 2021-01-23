from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from apps.cms.models import PublicationTerm, Publication, Term
from django.template.defaultfilters import slugify
import re

from bs4.element import Tag, NavigableString

mapping = {
    "Kingdom": "kingdom",
    "Subkingdom": "kingdom",
    "Superdivision": "phylum",
    "Division": "phylum",
    "Subdivision": "phylum",
    "Class": "class",
    "Subclass": "class",
    "Order": "order",
    "Family": "family",
    "Genus": "genus",
    "Species": "species"
}


def safe_list_get(l, idx, default=None):
    try:
        return l[idx]
    except IndexError:
        return default


def get_item(contents):
    arr = []
    for content in contents:
        if type(content) is NavigableString:
            arr.append(str(content).replace("–", "").strip())
        else:
            arr.append(content.get("href"))
            if arr[0] in ["Species", "Genus"]:
                names = content.find_all("em")
                f = str(safe_list_get(names, 0, "")).replace("<em>", "").replace("</em>", "").replace("×", "")
                s = str(safe_list_get(names, 1, "")).replace("<em>", "").replace("</em>", "").capitalize()
                arr.append("{} {}".format(f, s))
            else:
                names = content.find_all(text=True)[0].split(" ")
                arr.append(names[0])
    field = safe_list_get(arr, 0)
    return field, {
        "link": safe_list_get(arr, 1),
        "name": safe_list_get(arr, 2),
        "other_name": safe_list_get(arr, 3, "").capitalize()
    }


publication = Publication.objects.get(pk=7)


def usda(start, url, related):
    regex = re.compile('.*classind.*')
    r = requests.get(url)
    soup = BeautifulSoup(r.content, features="html.parser")
    elms = soup.find_all("td", {"class": regex})
    max_elms = max(list(map(lambda x: int(x.get("class")[0].replace("classind", "")), elms)))
    is_recurse = False
    while start <= max_elms:
        if start == max_elms and not is_recurse:
            break
        temp_elms = soup.find_all("td", {"class": "classind{}".format(start)})
        if len(temp_elms) == 0:
            is_recurse = True
        copy_related = related
        for elm in temp_elms:
            field, item = get_item(elm.contents)
            if field not in ["Variety", "Subspecies"] and field is not None and item.get("name"):
                term, is_created = Term.objects.get_or_create(slug=slugify(item.get("name")), defaults={
                    "title": item.get("name")
                })
                instance, is_created = PublicationTerm.objects.get_or_create(
                    term=term,
                    taxonomy=mapping.get(field, field),
                    publication=publication
                )
                if item.get("other_name"):
                    term, is_created = Term.objects.get_or_create(slug=slugify(item.get("other_name")), defaults={
                        "title": item.get("other_name")
                    })
                    instance_same, is_created = PublicationTerm.objects.get_or_create(
                        term=term,
                        taxonomy=mapping.get(field, field),
                        publication=publication
                    )
                    if instance not in instance_same.related.all():
                        instance_same.related.add(instance)
                else:
                    instance_same = None

                for r in related:
                    term_related = instance.related.all()
                    if r not in term_related:
                        instance.related.add(r)
                    if instance_same is not None:
                        term_related = instance_same.related.all()
                        if r not in term_related:
                            instance.related.add(r)

                print("{}: {} - {}".format(mapping.get(field, field), item.get("name"), instance.term.title))
                if is_recurse:
                    copy_related.append(instance)
                    usda(start, "https://plants.usda.gov{}".format(item.get("link")), copy_related)
                    copy_related.remove(instance)
        start = start + 1


class Command(BaseCommand):
    def handle(self, *args, **options):
        related = PublicationTerm.objects.filter(publication=publication, term__title__in=["Hepaticophyta"])
        url = "https://plants.usda.gov/java/ClassificationServlet?source=display&classid=Hepaticophyta"
        usda(0, url, list(related))
