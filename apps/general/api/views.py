from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['POST'])
def set_pub(request):
    if request.user.is_authenticated:
        profile = request.user.profile
        if profile.options is None:
            profile.options = {}
        profile.options["pub"] = request.data.get("pub", None)
        profile.save()
    return Response({})
