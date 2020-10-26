from apps.repository.models import GitUser
import requests

headers = {'Accept': 'application/vnd.github.mercy-preview+json', 'Origin': 'x-requested-with'}


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


def fetch_github(repo):
    if repo.id_github is not None:
        url = repo.id_github.replace("https://github.com/", "")
        r = requests.get("https://api.github.com/repos/" + url,
                         auth=('hoanglam.bk57@gmail.com', 'Hoanganhlam@no99'))
        if r.status_code == 200:
            data = r.json()
            backup = repo.data_github if repo.data_github is not None else {}
            backup["created_at"] = data.get("created_at")
            backup["updated_at"] = data.get("updated_at")
            backup["starsCount"] = data.get("stargazers_count")
            backup["forksCount"] = data.get("forks_count")
            owner = data.get("owner")
            git_user = GitUser.objects.filter(username=owner.get("login")).first()
            if git_user is None:
                git_user = GitUser(username=owner.get("login"), avatar_url=owner.get("avatar_url"))
            else:
                git_user.avatar_url = owner.get("avatar_url")
            git_user.save()
            repo.author = git_user
            repo.data_github = backup
            if repo.full_name is None:
                repo.full_name = url
            repo.save()


def fetch_npm(repo):
    url = repo.id_npm.replace("https://www.npmjs.com/package/", "")
    r = requests.get(
        "https://cors-anywhere.herokuapp.com/https://api.npms.io/v2/package/" + url,
        headers=headers)
    print(r.status_code)
    if r.status_code == 200:
        data = r.json()
        if data.get("collected").get("npm") is not None:
            repo.data_npm = data.get("collected").get("npm")
        if data.get("collected").get("github") is not None:
            repo.data_github = data.get("collected").get("github")
        if data.get("collected").get("source") is not None:
            repo.data_source = data.get("collected").get("source")
        if data.get("collected").get("metadata") is not None:
            repo.data_meta = data.get("collected").get("metadata")

        # 2020-04-07T12:46:26.075Z
        repo.last_fetch = data.get("analyzedAt")
        if repo.data_npm is not None:
            last_download = repo.data_npm.get("downloads")[-1:]
            if len(last_download) > 0:
                repo.data_npm["downloadsCount"] = last_download[0].get("count")
        repo.save()


def fetch_open_base(repo):
    url = "https://openbase.io/api/graphql"
    r = requests.post(url, json={"query": query, "variables": {"packageName": repo.name}})
    if r.status_code == 200:
        data = r.json()
        edges = data.get("data").get("package").get("collaborators").get("edges")
        for edg in edges:
            git_user = GitUser.objects.filter(email=edg.get("node").get("email")).first()
            if git_user is None:
                git_user = GitUser(
                    full_name=edg.get("node").get("name"),
                    avatar_url=edg.get("node").get("avatarUrl"),
                    email=edg.get("node").get("email")
                )
                git_user.save()
            if git_user not in repo.contributes.all():
                repo.contributes.add(git_user)
