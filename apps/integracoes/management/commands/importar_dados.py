from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.integracoes.conectores import executar
from apps.integracoes.models import FonteDados, Importacao


class Command(BaseCommand):
    help = "Importa os dados das fontes ativas (rodar toda noite, por exemplo pelo cron)."

    def add_arguments(self, parser):
        parser.add_argument("--camara", type=int, help="Só a câmara com este id.")
        parser.add_argument("--tipo", help="Só fontes deste tipo (ex.: pncp).")
        parser.add_argument("--desde", type=date.fromisoformat, help="Início do período (AAAA-MM-DD).")

    def handle(self, *args, camara=None, tipo=None, desde=None, **opcoes):
        fontes = FonteDados.objects.filter(ativa=True, camara__ativa=True).select_related("camara")
        if camara:
            fontes = fontes.filter(camara_id=camara)
        if tipo:
            if tipo not in FonteDados.Tipo.values:
                raise CommandError(f"Tipo desconhecido: {tipo}. Use um de: {', '.join(FonteDados.Tipo.values)}.")
            fontes = fontes.filter(tipo=tipo)
        erros = 0
        for fonte in fontes:
            r = executar(fonte, desde=desde)
            if r.situacao == Importacao.Situacao.ERRO:
                erros += 1
                self.stderr.write(f"{fonte.camara} / {fonte}: {r.mensagem}")
            else:
                self.stdout.write(f"{fonte.camara} / {fonte}: {r.novos} novos, {r.atualizados} atualizados.")
        if not fontes:
            self.stdout.write("Nenhuma fonte ativa.")
        elif erros:
            self.stderr.write(f"{erros} fonte(s) com erro. Veja Integrações > Importações no painel.")
