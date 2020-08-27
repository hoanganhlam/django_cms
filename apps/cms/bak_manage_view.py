@api_view(['GET', 'POST'])
def fetch_taxonomies(request):
    user_id = request.user.id if request.user.is_authenticated else None
    if request.method == "GET":
        p = get_paginator(request)
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TERM_TAXONOMIES(%s, %s, %s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               p.get("search"),
                               request.GET.get("order_by"),
                               user_id,
                               request.GET.get("taxonomy", None),
                               '{' + request.GET.get('taxonomies') + '}' if request.GET.get('taxonomies') else None,
                               request.GET.get('publication'),
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)
    elif request.method == "POST":
        errors = []
        term = None
        if request.data.get("term"):
            try:
                term = models.Term.objects.get(pk=int(request.data.get("term")))
            except models.Term.DoesNotExist:
                term = None
        else:
            if request.data.get("term_title"):
                term = models.Term.objects.filter(title=request.data.get("term_title")).first()
                if term is None:
                    term = models.Term.objects.create(title=request.data.get("term_title"))

        try:
            pub = models.Publication.objects.get(pk=int(request.data.get("publication")))
        except models.Publication.DoesNotExist:
            pub = None

        if term is None:
            errors.append({"term": "TERM_NONE"})
        if request.data.get("taxonomy") is None:
            errors.append({"taxonomy": "TAXONOMY_NONE"})
        if pub is None:
            errors.append({"publication": "PUBLICATION_NONE"})
        if len(errors) > 0:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        tax = models.PublicationTerm.objects.filter(
            publication=pub,
            taxonomy=request.data.get("taxonomy"),
            term=term
        ).first()
        if tax is None:
            tax = models.PublicationTerm.objects.create(
                publication=pub,
                taxonomy=request.data.get("taxonomy"),
                term=term
            )
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TAXONOMY(%s, %s, %s, %s)", [
                term.slug,
                request.data.get("publication"),
                request.data.get("taxonomy"),
                user_id
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)

    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_taxonomy(request, slug):
    user_id = request.user.id if request.user.is_authenticated else None
    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TAXONOMY(%s, %s, %s, %s)", [
                slug,
                request.GET.get("publication"),
                request.GET.get("taxonomy"),
                user_id
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)
    elif request.method == "PUT":
        pass
    elif request.method == "DELETE":
        pass
    return Response()


@api_view(['GET', 'POST'])
def fetch_posts(request):
    if request.method == "GET":
        p = get_paginator(request)
        user_id = request.user.id if request.user.is_authenticated else None
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_POSTS(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               p.get("search"),
                               request.GET.get("order_by"),
                               user_id,
                               request.GET.get("post_type", None),
                               '{' + request.GET.get('taxonomies') + '}' if request.GET.get('taxonomies') else None,
                               '{' + request.GET.get('publications') + '}' if request.GET.get('publications') else None,
                               True
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)
    elif request.method == "POST":
        pass


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_post(request, slug):
    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_POST(%s, %s)", [
                int(slug) if slug.isnumeric() else slug,
                request.GET.get("uid") is not None
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)
    elif request.method == "PUT":
        pass
    elif request.method == "DELETE":
        pass
    return Response()
