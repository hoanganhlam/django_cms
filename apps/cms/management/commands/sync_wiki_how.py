from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from apps.media.models import Media
import json
import random
import requests
from django.template.defaultfilters import slugify
import os
import re
from markdownify import markdownify as md


def convert_checklist(data):
    return {
        "title": data.get("title"),
        "child": list(map(lambda x: {
            "title": x.get("title"),
            "detail": md(x.get("content")),
        }, data.get("tasks")))
    }


class Command(BaseCommand):
    def handle(self, *args, **options):
        pub_todo = Publication.objects.get(pk=27)
        pub_question = Publication.objects.get(pk=14)
        name_folders = os.listdir("data_wiki_how")
        name_folders.sort()
        break_point = "Completed Commuting"
        start = False
        print(name_folders)
        for folder in name_folders:
            if not start:
                if break_point == folder:
                    start = True
                continue
            for x in os.walk("data_wiki_how/{folder}".format(folder=folder)):
                term, is_created = Term.objects.get_or_create(
                    slug=slugify(folder),
                    defaults={
                        "title": folder
                    }
                )
                p_term_todo, is_created = PublicationTerm.objects.get_or_create(
                    term=term,
                    taxonomy="tag",
                    publication=pub_todo
                )
                p_term_question, is_created = PublicationTerm.objects.get_or_create(
                    term=term,
                    taxonomy="tag",
                    publication=pub_question
                )
                x[2].sort()
                for u in x[2]:
                    path = x[0] + "/" + u
                    with open(path) as json_file:
                        data = json.load(json_file)
                        title = data.get("meta").get("title")
                        slug = slugify(title)
                        description = re.sub('\[[0-9]\]', '', md(data.get("meta").get("description")))
                        if description is None:
                            description = ""
                        meta = {
                            "checklist": list(map(convert_checklist, data.get("todo_list"))),
                            "seo": {
                                "title": "How to {title} step by step".format(
                                    title=data.get("meta").get("title").lower(),
                                    le=len(data.get("todo_list"))
                                )
                            }
                        }

                        test = Post.objects.filter(primary_publication=pub_todo, slug=slug).first()
                        if test is None:
                            print(title)
                            test = Post.objects.create(
                                title=title,
                                description=description if len(description) < 499 else description[:499],
                                meta=meta,
                                show_cms=True,
                                post_type="post",
                                primary_publication=pub_todo,
                                is_guess_post=True,
                                status="POSTED"
                            )
                        test.terms.add(p_term_todo)
                        print(slug)
                        questions = list(map(lambda item: {
                            "title": item.get("title"),
                            "description": item.get("content")
                                             .replace("Support wikiHow by unlocking this staff-researched answer.\n",
                                                      "")
                                             .replace("Support wikiHow by unlocking this expert answer.\n", "")
                        }, data.get("questions")))
                        for q in questions:
                            if len(title) < 50:
                                term_2, is_created = Term.objects.get_or_create(
                                    slug=slugify(title),
                                    defaults={
                                        "title": title
                                    }
                                )
                                p_term_2, is_created = PublicationTerm.objects.get_or_create(
                                    term=term_2,
                                    taxonomy="tag",
                                    publication=pub_question
                                )
                            else:
                                p_term_2 = None

                            title = q.get("title")
                            if len(title) > 199:
                                continue
                            slug = slugify(q.get("title"))
                            test = Post.objects.filter(primary_publication=pub_question, slug=slug).first()
                            if test is None:
                                test = Post.objects.create(
                                    title=title,
                                    slug=slug,
                                    description=q.get("description") if len(q.get("description")) < 499 else q.get(
                                        "description")[:499],
                                    content=q.get("description") if len(q.get("description")) > 499 else None,
                                    show_cms=True,
                                    post_type="question",
                                    primary_publication=pub_question,
                                    is_guess_post=True,
                                    status="POSTED",
                                    options={
                                        "primary_term": p_term_2.id if p_term_2 else p_term_question.id
                                    }
                                )
                            else:
                                print("A")
                                test.title = title
                                test.save()
                            test.terms.add(p_term_question)
                            if p_term_2:
                                test.terms.add(p_term_2)
                            print(slug)
            print("Completed {}".format(folder))
            print("================================================")
