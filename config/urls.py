from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.camaras import views as portal
from apps.conteudo import views as conteudo
from apps.camaras.anexos import baixar_anexo_equipe
from apps.legislativo import views as legislativo
from apps.noticias import views as noticias
from apps.transparencia import views as transparencia

admin.site.site_header = "Portal das Câmaras: painel"
admin.site.site_title = "Painel"
admin.site.index_title = "Início"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("anexos/<path:caminho>", baixar_anexo_equipe, name="anexo_equipe"),
    path("", portal.inicio, name="inicio"),
    path("acessibilidade/", portal.acessibilidade, name="acessibilidade"),
    path("privacidade/", portal.privacidade, name="privacidade"),
    path("institucional/mesa-diretora/", conteudo.mesa_diretora, name="mesa_diretora"),
    path("institucional/<slug:slug>/", conteudo.pagina, name="pagina"),
    path("noticias/", noticias.lista, name="noticias"),
    path("noticias/<slug:slug>/", noticias.detalhe, name="noticia"),
    path("vereadores/", legislativo.vereadores, name="vereadores"),
    path("vereadores/<int:pk>/", legislativo.vereador, name="vereador"),
    path("legislacao/", legislativo.normas, name="normas"),
    path("sessoes/", legislativo.sessoes, name="sessoes"),
    path("sessoes/<int:pk>/", legislativo.sessao, name="sessao"),
    path("materias/", legislativo.materias, name="materias"),
    path("materias/<int:pk>/", legislativo.materia, name="materia"),
    path("transparencia/", transparencia.indice, name="transparencia"),
    path("transparencia/<slug:slug>/", transparencia.categoria, name="transparencia_categoria"),
    path("esic/", include("apps.esic.urls")),
    path("ouvidoria/", include("apps.ouvidoria.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
