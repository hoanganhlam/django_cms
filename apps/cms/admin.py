from django.contrib import admin
from .models import Post, Term

# Register your models here.
admin.site.register((Post, Term))
