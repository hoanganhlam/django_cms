#!/usr/bin/python
# -*- coding: utf8 -*-

from django.shortcuts import render_to_response, render
from django.template import RequestContext
# from django.conf.urls.static import static
# from django.contrib.staticfiles import storage
from django.contrib.staticfiles.templatetags.staticfiles import static

# HTTP Error 400
def bad_request(request, exception=None, template_name='templates/400.html'):
    context = {"static": static}
    return render(request, template_name, context, content_type='application/xhtml+xml')


# HTTP Error 403
def permission_denied(request, exception=None, template_name='templates/403.html'):
    context = {"static": static}
    return render(request, template_name, context, content_type='application/xhtml+xml')


# HTTP Error 404
def page_not_found(request, exception=None, template_name='templates/404.html'):
    context = {"static": static}
    return render(request, template_name, context, content_type='application/xhtml+xml')


# HTTP Error 500
def server_error(request, exception=None, template_name='templates/500.html'):
    context = {"static": static}
    # context = RequestContext(request)
    # response = render_to_response('500.html', context)
    # response.status_code = 500
    # return response

    return render(request, template_name, context, content_type='application/xhtml+xml')
