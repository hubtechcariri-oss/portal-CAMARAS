#!/usr/bin/env bash
# Roda uma vez, quando o Codespace é criado.
set -euo pipefail
pip install --user -r requirements.txt

until python -c "import psycopg; psycopg.connect(host='db', user='portal', password='portal', dbname='portal')" 2>/dev/null; do
  echo "Aguardando o PostgreSQL..."; sleep 2
done

python manage.py migrate --noinput

HOSTS=(--host localhost)
if [ -n "${CODESPACE_NAME:-}" ]; then
  HOSTS+=(--host "${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}")
fi
python manage.py criar_demo "${HOSTS[@]}"

# Usuário do painel, apenas para a demonstração. Não use em produção.
DJANGO_SUPERUSER_PASSWORD=demo123 python manage.py createsuperuser --noinput \
  --username admin --email admin@exemplo.leg.br 2>/dev/null || echo "Usuário admin já existe."
