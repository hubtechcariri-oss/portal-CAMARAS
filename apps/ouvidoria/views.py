from django.shortcuts import redirect, render

from .forms import ConsultaForm, ManifestacaoForm
from .models import Manifestacao


def nova(request):
    form = ManifestacaoForm(request.POST or None)
    if request.method == "POST":
        form.instance.camara = request.camara
        if form.is_valid():
            manifestacao = form.save()
            request.session["ouvidoria_ultima"] = manifestacao.pk
            return redirect("ouvidoria:confirmacao")
    return render(request, "portal/ouvidoria/nova.html", {"form": form})


def confirmacao(request):
    pk = request.session.pop("ouvidoria_ultima", None)
    manifestacao = Manifestacao.objects.da_camara(request.camara).filter(pk=pk).first() if pk else None
    if not manifestacao:
        return redirect("ouvidoria:nova")
    return render(request, "portal/ouvidoria/confirmacao.html", {"manifestacao": manifestacao})


def consulta(request):
    form = ConsultaForm(request.GET or None)
    manifestacao = None
    nao_encontrada = False
    if form.is_valid():
        manifestacao = (
            Manifestacao.objects.da_camara(request.camara)
            .filter(
                protocolo=form.cleaned_data["protocolo"].strip(),
                codigo_consulta=form.cleaned_data["codigo"].strip().upper(),
            )
            .first()
        )
        nao_encontrada = manifestacao is None
    contexto = {"form": form, "manifestacao": manifestacao, "nao_encontrada": nao_encontrada}
    return render(request, "portal/ouvidoria/consulta.html", contexto)
