from django.http import Http404
from django.shortcuts import redirect, render

from apps.camaras.anexos import resposta_arquivo

from .forms import ConsultaForm, ManifestacaoForm
from .models import Manifestacao


def nova(request):
    form = ManifestacaoForm(request.POST or None, request.FILES or None)
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


def baixar_anexo(request, qual):
    """Download do anexo pelo cidadão: exige protocolo e código de consulta corretos."""
    form = ConsultaForm(request.GET or None)
    if qual not in ("anexo", "anexo_resposta") or not form.is_valid():
        raise Http404
    obj = (
        Manifestacao.objects.da_camara(request.camara)
        .filter(
            protocolo=form.cleaned_data["protocolo"].strip(),
            codigo_consulta=form.cleaned_data["codigo"].strip().upper(),
        )
        .first()
    )
    if obj is None:
        raise Http404
    return resposta_arquivo(getattr(obj, qual))
