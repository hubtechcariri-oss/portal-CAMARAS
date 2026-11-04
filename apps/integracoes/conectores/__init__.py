"""Conectores: cada fonte de dados tem um, com o mesmo formato.

Um conector recebe a fonte e o início do período, busca os dados na origem e grava
nas tabelas do portal, devolvendo quantos registros são novos e quantos mudaram.
Para incluir um fornecedor novo, escreva uma subclasse de `Conector`, registre-a em
`CONECTORES` e acrescente o tipo em `FonteDados.Tipo`.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

CARGA_INICIAL_DIAS = 365  # primeira importação: busca o último ano
SOBREPOSICAO_DIAS = 7     # depois: volta uma semana antes do último sucesso, para pegar retificações


class ErroDeImportacao(Exception):
    """Erro esperado (configuração faltando, origem fora do ar): vira mensagem legível no registro."""


@dataclass
class Resultado:
    novos: int = 0
    atualizados: int = 0
    avisos: list = field(default_factory=list)

    def contar(self, criado):
        if criado:
            self.novos += 1
        else:
            self.atualizados += 1


class Conector:
    rotulo = ""

    def importar(self, fonte, desde: date, ate: date) -> Resultado:  # pragma: no cover - interface
        raise NotImplementedError


CONECTORES = {}


def registrar(tipo):
    def decorador(classe):
        CONECTORES[tipo] = classe
        return classe
    return decorador


def periodo_padrao(fonte, hoje=None):
    hoje = hoje or timezone.localdate()
    if fonte.ultimo_sucesso:
        return timezone.localtime(fonte.ultimo_sucesso).date() - timedelta(days=SOBREPOSICAO_DIAS), hoje
    return hoje - timedelta(days=CARGA_INICIAL_DIAS), hoje


def executar(fonte, desde=None, ate=None):
    """Roda o conector da fonte e grava o resultado em `Importacao`. Nunca levanta exceção."""
    from apps.integracoes.models import Importacao

    from . import pncp  # noqa: F401  (registra os conectores)

    padrao_desde, padrao_ate = periodo_padrao(fonte)
    desde, ate = desde or padrao_desde, ate or padrao_ate
    registro = Importacao.objects.create(fonte=fonte, desde=desde)
    fonte.ultima_execucao = registro.iniciada_em
    try:
        classe = CONECTORES.get(fonte.tipo)
        if classe is None:
            raise ErroDeImportacao(f"Não há conector para o tipo “{fonte.tipo}”.")
        with transaction.atomic():
            resultado = classe().importar(fonte, desde, ate)
        registro.situacao = Importacao.Situacao.SUCESSO
        registro.novos, registro.atualizados = resultado.novos, resultado.atualizados
        registro.mensagem = "\n".join(resultado.avisos)
        fonte.ultimo_sucesso = timezone.now()
    except ErroDeImportacao as erro:
        registro.situacao, registro.mensagem = Importacao.Situacao.ERRO, str(erro)
    except Exception as erro:  # origem mudou de formato, rede caiu etc.: registra e segue para a próxima
        registro.situacao = Importacao.Situacao.ERRO
        registro.mensagem = f"Erro inesperado: {erro.__class__.__name__}: {erro}"
    registro.terminada_em = timezone.now()
    registro.save()
    fonte.save(update_fields=["ultima_execucao", "ultimo_sucesso", "atualizado_em"])
    return registro
