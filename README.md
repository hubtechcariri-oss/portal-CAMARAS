# Portal das Câmaras

SaaS de portal institucional e de transparência para câmaras municipais. Um código e um banco atendem várias câmaras, e cada uma responde no próprio domínio.

## O que já existe (Fase 1, início)

- **Multi-tenant por domínio.** O middleware `apps/camaras/middleware.py` identifica a câmara pelo `Host`. Um domínio desconhecido recebe 404.
- **Isolamento.** Todo conteúdo herda `ModeloDaCamara`. As views consultam `Modelo.objects.da_camara(request.camara)`, e o admin (`AdminDaCamara`) mostra e grava apenas dados das câmaras do usuário. Testes em `apps/camaras/tests/test_isolamento.py`.
- **Portal público acessível**, renderizado no servidor: atalhos de teclado do eMAG, alto contraste, ajuste de fonte, VLibras e layout responsivo.
- **Vereadores, legislaturas, notícias.**
- **Sessões plenárias**: pauta, ata, vídeo, presenças e matérias deliberadas.
- **Matérias legislativas**: autoria (vereadores e/ou autor externo), situação, tramitação com resultado de votação e vínculo com a norma gerada. Filtros por tipo, ano, situação, autor e busca textual. Perfil do vereador mostra matérias de autoria e presenças.
- **Legislação** com busca em português que ignora acentos (configuração `portugues` do Postgres: `unaccent` + stemmer).
- **Transparência**: um catálogo de categorias comum à plataforma (editável no admin, sem mexer em código) e documentos por câmara, com arquivo, link externo ou ambos.
- **Dados abertos**: as listagens de legislação e transparência aceitam `?formato=csv` ou `?formato=json`.
- **e-SIC**: protocolo sequencial por câmara, código secreto de consulta, prazo de 20 dias com uma prorrogação de 10, indicador de vencimento e aviso de privacidade.

## Ver no navegador sem instalar nada (GitHub Codespaces)

1. No GitHub, abra o repositório e clique em **Code → Codespaces → Create codespace on main**.
2. Espere a preparação, que leva alguns minutos na primeira vez. Ela instala as dependências, cria o banco e carrega a câmara de demonstração.
3. O portal abre sozinho numa aba. Se não abrir, use a aba **PORTS**, porta 8000, ícone do globo.
4. Para o painel, acrescente `/admin/` ao endereço. Usuário `admin`, senha `demo123` (vale só para a demonstração; troque se tornar a porta pública).

Sempre que o Codespace é aberto ou reconectado, `iniciar.sh` puxa a `main`, aplica as migrações e reinicia o servidor. Para atualizar na hora, rode `bash .devcontainer/iniciar.sh` no terminal.

O Codespace para sozinho quando fica ocioso e consome a cota gratuita mensal do GitHub. Exclua-o em github.com/codespaces quando não precisar mais.

## Anexos (e-SIC e Ouvidoria)

O cidadão pode anexar um arquivo ao pedido ou à manifestação, e o atendente pode anexar um arquivo à resposta. Esses arquivos podem conter dados pessoais, por isso:

- ficam em `ANEXOS_ROOT` (padrão `anexos_privados/`), **fora** da pasta pública de mídia. Em produção, use um volume persistente com backup;
- o cidadão só baixa o anexo informando protocolo e código; a equipe só baixa anexos da própria câmara, pelo painel (`/anexos/...`);
- o arquivo é aceito com até 10 MB e nos formatos PDF, imagens, documentos e planilhas comuns (`ANEXOS_EXTENSOES` em `settings.py`). É sempre entregue como download.

## Imagens e arquivos pelo painel

Tudo o que aparece no portal pode ser trocado pelo painel, sem mexer em código:

| O quê | Onde no painel |
|---|---|
| Brasão, cor principal, redes sociais, endereço e contatos | Câmaras › Identidade do portal |
| Banners rotativos da página inicial | Conteúdo › Banners |
| Páginas institucionais (com imagem) | Conteúdo › Páginas |
| Imagens das notícias | Notícias |
| Fotos dos vereadores | Legislativo › Vereadores |
| PDFs de leis, pautas, atas, matérias e transparência | no cadastro de cada item |

Os arquivos ficam em `media/camara_<id>/<tipo>/<ano>/`, separados por câmara. Imagens aceitam JPG, PNG e WebP até 5 MB; documentos, PDF e formatos de escritório até 30 MB. Cada espaço do layout tem um tamanho fixo, mostrado ao lado do campo de envio:

| Imagem | Tamanho ideal | Mínimo aceito | Ao salvar |
|---|---|---|---|
| Banner | 1600 × 500 px | 1200 × 375 px | recorta pelo centro e reduz |
| Notícia e página | 1200 × 675 px (16:9) | 800 × 450 px | recorta pelo centro e reduz |
| Foto de vereador | 600 × 600 px | 300 × 300 px | recorta pelo centro e reduz |
| Brasão | 512 × 512 px (PNG transparente) | 128 × 128 px | só reduz, sem recorte |

Os tamanhos ficam em `FORMATOS`, em `apps/camaras/midia.py`.

Para quem cuida da comunicação da câmara, coloque o usuário no grupo **Comunicação** (criado automaticamente) e vincule-o à câmara.

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

Veja a seção "Fases do MVP" em `docs/proposta-inicial.md`. Os principais: painel de conformidade PNTP, alertas de prazo, comissões, importação em massa, RLS e trilha de auditoria.
