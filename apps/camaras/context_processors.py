def camara(request):
    return {"camara": getattr(request, "camara", None)}
