from rest_framework.decorators import api_view
from rest_framework.response import Response
from utils.web_checker import get_web_meta
import feedparser


@api_view(['POST'])
def set_pub(request):
    if request.user.is_authenticated:
        profile = request.user.profile
        if profile.options is None:
            profile.options = {}
        profile.options["pub"] = request.data.get("pub", None)
        profile.save()
    return Response({})


@api_view(['POST'])
def set_term(request):
    if request.user.is_authenticated:
        profile = request.user.profile
        if profile.options is None:
            profile.options = {}
        profile.options["terms"] = request.data.get("terms", [])
        profile.save()
    return Response({})


@api_view(['GET'])
def fetch_url(request):
    url = request.GET.get("url")
    if url:
        return Response(get_web_meta(url))
    elif request.GET.get("rss"):
        return Response(feedparser.parse(request.GET.get("rss")))
    else:
        return Response({})
