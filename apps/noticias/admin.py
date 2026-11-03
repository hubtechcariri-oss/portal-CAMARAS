from django.contrib import admin

from apps.camaras.admin_mixins import AdminDaCamara

from .models import Noticia


@admin.register(Noticia)
class NoticiaAdmin(AdminDaCamara):
    list_display = ["titulo", "publicada_em", "publicada"]
    list_filter = ["publicada"]
    search_fields = ["titulo", "corpo"]
    prepopulated_fields = {"slug": ["titulo"]}
    date_hierarchy = "publicada_em"
