# Hospedagem compartilhada (DirectAdmin/cPanel com "Setup Python App")

Para hospedagens sem SSH, com MySQL/MariaDB e Passenger (ex.: Acquahost). Em servidor próprio, prefira PostgreSQL + gunicorn (Dockerfile).

1. **Banco:** crie um banco MySQL e um usuário com todas as permissões nele.
2. **Aplicação Python:** versão 3.11; raiz `portal` (fora do public_html); URL o domínio da câmara;
   arquivo de inicialização `passenger_wsgi.py`; ponto de entrada `application`.
3. **Variáveis de ambiente** da aplicação:

   | Variável | Valor |
   |---|---|
   | `DB_ENGINE` | `mysql` |
   | `DB_NAME`, `DB_USER`, `DB_PASSWORD` | os do passo 1 |
   | `DJANGO_DEBUG` | `false` |
   | `DJANGO_SERVIR_MEDIA` | `true` |
   | `DJANGO_ALLOWED_HOSTS` | o domínio, ex.: `cm.caririinovacao.com.br` |

   A `SECRET_KEY` é gerada sozinha no primeiro acesso e fica em `portal/.chave_secreta`.
4. **Código:** crie `portal/implantar.py` (copie do GitHub) e rode-o em "Executar script Python".
   Ele baixa a main, migra o banco, coleta os estáticos e reinicia. Depois, instale as dependências com
   `requirements-hospedagem.txt` e rode `implantar.py --sem-baixar` de novo.
5. **Atualizar:** rode `implantar.py` de novo (ou agende como tarefa cron).

Detalhes do MySQL: as datas ficam gravadas no horário de Brasília (não exige as tabelas de fuso do MySQL) e a
busca de leis e matérias é por trecho, sem acento (a collation `utf8mb4_unicode_ci` ignora acentos).
