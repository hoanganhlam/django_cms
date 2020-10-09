from rest_framework.decorators import api_view
from rest_framework.response import Response
from utils.web_checker import get_web_meta


@api_view(['POST'])
def set_pub(request):
    if request.user.is_authenticated:
        profile = request.user.profile
        if profile.options is None:
            profile.options = {}
        profile.options["pub"] = request.data.get("pub", None)
        profile.save()
    return Response({})


@api_view(['GET'])
def fetch_url(request):
    url = request.GET.get("url")
    if url:
        return Response(get_web_meta(url))
    else:
        return Response({})
