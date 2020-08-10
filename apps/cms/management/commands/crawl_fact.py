from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from apps.cms.models import Post, Publication, Term, TermTaxonomy
from django.contrib.auth.models import User

user = User.objects.get(pk=1)
pub = Publication.objects.get(pk=4)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('uri', type=str, help='Indicates the number of users to be created')
        parser.add_argument('name', type=str, help='Indicates the number of users to be created')

    def handle(self, *args, **options):
        req = requests.get(options.get("uri"))
        term = Term.objects.filter(title=options.get("name")).first()
        if term is None:
            term = Term.objects.create(title=options.get("name"))
        pri_term = TermTaxonomy.objects.filter(taxonomy="object", term=term).first()
        if pri_term is None:
            pri_term = TermTaxonomy.objects.create(taxonomy="object", term=term)

        soup = BeautifulSoup(req.text, "html5lib")
        a_list = soup.select(".factsList li")
        t_list = soup.select(".divInnerHashTag a")
        r_list = soup.select(".divReferences .pReference")
        reference = {}
        tags = []
        for a in r_list:
            if len(a.select("a")) > 0:
                reference[a.select("sup")[0].string] = {
                    "href": a.select("a")[0]['href'],
                    "title": a.select("a")[0].string

                }
        for a in t_list:
            title = a.string[1:]
            if title:
                term = Term.objects.filter(title=title).first()
                if term is None:
                    term = Term.objects.create(title=title)
                tag = TermTaxonomy.objects.filter(taxonomy="tag", term=term).first()
                if tag is None:
                    tag = TermTaxonomy.objects.create(taxonomy="tag", term=term)
                tags.append(tag)
        for a in a_list:
            description = a.text
            source = None
            if len(a.select("sub")) > 0:
                x = a.select("sub")[0].string
                description = description.replace(x, '')
                source = reference.get(x[1:len(x) - 1])
            if len(description.split(".")) > 0:
                title = description.split(".")[0][:199]
                fact = Post.objects.filter(title=title).first()
                if fact is None:
                    fact = Post.objects.create(
                        user=user,
                        primary_publication=pub,
                        title=title,
                        description=description,
                        meta={"source": source},
                        status="POSTED",
                        post_type="fact"
                    )
                    fact.publications.add(pub)
                    fact.post_terms.add(pri_term)
                    for tag in tags:
                        fact.post_terms.add(tag)
                    print(fact.id)
