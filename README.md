# Portal das Câmaras

SaaS de portal institucional e de transparência para câmaras municipais. Um código e um banco atendem várias câmaras, e cada uma responde no próprio domínio.

## O que já existe (Fase 1, início)

- **Multi-tenant por domínio.** O middleware `apps/camaras/middleware.py` identifica a câmara pelo `Host`. Um domínio desconhecido recebe 404.
- **Isolamento.** Todo conteúdo herda `ModeloDaCamara`. As views consultam `Modelo.objects.da_camara(request.camara)`, e o admin (`AdminDaCamara`) mostra e grava apenas dados das câmaras do usuário. Testes em `apps/camaras/tests/test_isolamento.py`.
- **Portal público acessível**, renderizado no servidor: atalhos de teclado do eMAG, alto contraste, ajuste de fonte, VLibras e layout responsivo.
- **Vereadores, legislaturas, notícias.**
- **Legislação** com busca em português que ignora acentos (configuração `portugues` do Postgres: `unaccent` + stemmer).
- **Transparência**: um catálogo de categorias comum à plataforma (editável no admin, sem mexer em código) e documentos por câmara, com arquivo, link externo ou ambos.
- **Dados abertos**: as listagens de legislação e transparência aceitam `?formato=csv` ou `?formato=json`.
- **e-SIC**: protocolo sequencial por câmara, código secreto de consulta, prazo de 20 dias com uma prorrogação de 10, indicador de vencimento e aviso de privacidade.

## Rodar localmente

Com Docker:

```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py criar_demo --host localhost
docker compose exec web python manage.py createsuperuser
```

Sem Docker, com um Postgres 14 ou mais recente na máquina:

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py criar_demo --host localhost
.venv/bin/python manage.py runserver
```

Portal: http://localhost:8000/. Painel: http://localhost:8000/admin/.

Para dar acesso a um servidor da câmara: crie o usuário com "membro da equipe" marcado e as permissões dos módulos, e vincule-o à câmara em *Câmaras → Membros da equipe*.

## Testes

```bash
.venv/bin/python manage.py test
```

Os testes exigem Postgres, porque a busca textual e a extensão `unaccent` são específicas dele.

## Decisões de arquitetura

- **Monólito modular** (`apps/*`). O volume de acesso de portais de câmaras não justifica microsserviços.
- **Banco compartilhado com `camara_id`.** Hoje o isolamento é feito na aplicação e coberto por testes. O próximo passo previsto é ativar o Row-Level Security do Postgres como segunda barreira.
- **Catálogo de transparência como dado, não como código**, porque a matriz PNTP muda todo ano. O campo `obrigatoria` deve ser marcado conforme a matriz vigente e o Tribunal de Contas do estado.
- **Sem cookies de rastreamento.** O portal usa apenas o cookie técnico de sessão, por isso não exibe um banner de consentimento.

## Próximos passos

Veja a seção "Fases do MVP" em `docs/proposta-inicial.md`. Os principais: painel de conformidade PNTP, alertas de prazo, sessões e matérias, importação em massa, RLS e trilha de auditoria.
