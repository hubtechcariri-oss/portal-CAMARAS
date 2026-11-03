from django.http import Http404
from django.shortcuts import redirect, render

from apps.camaras.anexos import resposta_arquivo

from .forms import ConsultaForm, PedidoForm
from .models import Pedido


def novo(request):
    form = PedidoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        pedido = form.save(commit=False)
        pedido.camara = request.camara
        pedido.save()
        request.session["esic_ultimo"] = pedido.pk
        return redirect("esic:confirmacao")
    return render(request, "portal/esic/novo.html", {"form": form})


def confirmacao(request):
    pk = request.session.pop("esic_ultimo", None)
    pedido = Pedido.objects.da_camara(request.camara).filter(pk=pk).first() if pk else None
    if not pedido:
        return redirect("esic:novo")
    return render(request, "portal/esic/confirmacao.html", {"pedido": pedido})


def consulta(request):
    form = ConsultaForm(request.GET or None)
    pedido = None
    nao_encontrado = False
    if form.is_valid():
        pedido = (
            Pedido.objects.da_camara(request.camara)
            .filter(
                protocolo=form.cleaned_data["protocolo"].strip(),
                codigo_consulta=form.cleaned_data["codigo"].strip().upper(),
            )
            .first()
        )
        nao_encontrado = pedido is None
    contexto = {"form": form, "pedido": pedido, "nao_encontrado": nao_encontrado}
    return render(request, "portal/esic/consulta.html", contexto)


def baixar_anexo(request, qual):
    """Download do anexo pelo cidadão: exige protocolo e código de consulta corretos."""
    form = ConsultaForm(request.GET or None)
    if qual not in ("anexo", "anexo_resposta") or not form.is_valid():
        raise Http404
    obj = (
        Pedido.objects.da_camara(request.camara)
        .filter(
            protocolo=form.cleaned_data["protocolo"].strip(),
            codigo_consulta=form.cleaned_data["codigo"].strip().upper(),
        )
        .first()
    )
    if obj is None:
        raise Http404
    return resposta_arquivo(getattr(obj, qual))
