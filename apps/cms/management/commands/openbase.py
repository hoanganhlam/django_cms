import requests
from django.core.management.base import BaseCommand
from apps.repository.models import Repository, GitUser
from django.db.models import Q
from apps.repository.management.commands.fetcher import fetch_open_base

query = """
query ContributorsQuery($packageName: String!){
    package(name: $packageName) {
        collaboratorCount
        collaborators(first: 200) {
            edges {
                node {
                    avatarUrl
                    bio
                    commitCount
                    mergedPullRequestCount
                    name
                    pullRequestCount
                    email
                }
            }
        }
        id
    }
}
"""


class Command(BaseCommand):
    def handle(self, *args, **options):
        q = ~Q(id_github=None) & Q(contributes=None)
        queryset = Repository.objects.filter(q)
        for repo in queryset:
            fetch_open_base(repo)
