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
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | o endereço com https, ex.: `https://cm.caririinovacao.com.br` |

   A `SECRET_KEY` é gerada sozinha no primeiro acesso e fica em `portal/.chave_secreta`.
4. **Código:** envie `implantar.py` (do GitHub) para a pasta `portal` pelo gerenciador de arquivos e rode-o
   em "Executar script Python". Ele baixa a main, instala as dependências, migra o banco, coleta os
   estáticos e reinicia. Não use o botão "Executar Pip Install": ele desiste com "Web application is
   inaccessible" enquanto o site ainda não sobe.
5. **Câmara e administrador:** `implantar.py --sem-baixar --demo DOMINIO` cria a câmara de demonstração;
   para o superusuário, defina `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` e
   `DJANGO_SUPERUSER_PASSWORD`, rode `implantar.py --sem-baixar --admin` e apague a variável da senha.
6. **Página do subdomínio:** se aparecer "Este é um espaço reservado para o subdomínio", renomeie
   `domains/<dominio>/public_html/index.html` (o servidor entrega esse arquivo antes da aplicação).
7. **Atualizar:** rode `implantar.py` de novo (ou agende como tarefa cron).

Detalhes do MySQL: as datas ficam gravadas no horário de Brasília (não exige as tabelas de fuso do MySQL) e a
busca de leis e matérias é por trecho, sem acento (a collation `utf8mb4_unicode_ci` ignora acentos).
