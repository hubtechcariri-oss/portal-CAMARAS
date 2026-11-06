"""Instala ou atualiza o portal numa hospedagem compartilhada sem SSH (DirectAdmin/cPanel "Setup Python App").

Rode pelo campo "Executar script Python" do painel da aplicação:

    implantar.py                    baixa a main do GitHub, migra o banco e reinicia a aplicação
    implantar.py --sem-baixar       só migra, coleta os arquivos estáticos e reinicia
    implantar.py --demo HOST        também cria a câmara de demonstração respondendo em HOST
    implantar.py --admin            cria o superusuário com DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD
                                    (variáveis definidas no painel; a senha nunca aparece na saída)

Antes, no painel, instale as dependências com o arquivo requirements-hospedagem.txt.
Ver docs/hospedagem-compartilhada.md.
"""

import io
import os
import sys
import tarfile
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PACOTE = "https://codeload.github.com/hubtechcariri-oss/portal-CAMARAS/tar.gz/refs/heads/main"
# O que é da instalação e nunca vem do GitHub (ou não precisa vir).
PRESERVAR = ("media/", "anexos_privados/", "staticfiles/", ".chave_secreta", "docs/", "tmp/")


def baixar():
    print(f"Baixando {PACOTE} …", flush=True)
    with urllib.request.urlopen(PACOTE, timeout=120) as resposta:
        dados = resposta.read()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(dados), mode="r:gz") as pacote:
        for membro in pacote.getmembers():
            partes = membro.name.split("/", 1)
            if len(partes) < 2 or not partes[1]:
                continue
            caminho = partes[1]
            if (caminho + "/").startswith(PRESERVAR) or not (membro.isfile() or membro.isdir()):
                continue
            membro.name = caminho
            pacote.extract(membro, RAIZ, filter="data")
            total += membro.isfile()
    print(f"{total} arquivos atualizados.", flush=True)


def django():
    sys.path.insert(0, str(RAIZ))
    os.chdir(RAIZ)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django as dj

    dj.setup()
    from django.core.management import call_command

    return call_command


def main(args):
    if "--sem-baixar" not in args:
        baixar()
    comando = django()
    comando("migrate", interactive=False, verbosity=1)
    comando("collectstatic", interactive=False, verbosity=0)
    print("Banco migrado e arquivos estáticos coletados.", flush=True)
    if "--demo" in args:
        host = args[args.index("--demo") + 1]
        comando("criar_demo", hosts=[host])
    if "--admin" in args:
        from django.contrib.auth import get_user_model

        nome = os.environ.get("DJANGO_SUPERUSER_USERNAME", "")
        if not nome or not os.environ.get("DJANGO_SUPERUSER_PASSWORD"):
            print("Defina DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL e DJANGO_SUPERUSER_PASSWORD no painel.")
        elif get_user_model().objects.filter(username=nome).exists():
            print(f"O usuário {nome} já existe; nada a fazer.")
        else:
            comando("createsuperuser", interactive=False)
            print(f"Superusuário {nome} criado. Apague DJANGO_SUPERUSER_PASSWORD do painel.")
    (RAIZ / "tmp").mkdir(exist_ok=True)
    (RAIZ / "tmp" / "restart.txt").touch()  # o Passenger recarrega a aplicação
    print("Pronto: aplicação reiniciada.", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
