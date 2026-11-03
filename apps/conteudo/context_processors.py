from .models import Pagina


def menu(request):
    """Páginas que aparecem nos submenus, agrupadas por menu."""
    camara = getattr(request, "camara", None)
    if not camara:
        return {}
    grupos = {}
    for p in Pagina.objects.da_camara(camara).filter(publicada=True).exclude(menu="").only("titulo", "slug", "menu"):
        grupos.setdefault(p.menu, []).append(p)
    return {"paginas_menu": grupos}
