#!/usr/bin/env bash
# Roda sempre que o Codespace é aberto ou reconectado:
# atualiza o código da main, aplica migrações e (re)inicia o servidor.
set -u
cd "$(dirname "$0")/.."

# O proxy de portas do Codespaces reescreve o Origin dos formulários para https://localhost:8000.
export DJANGO_CSRF_TRUSTED_ORIGINS="https://*.app.github.dev,https://localhost:8000"
export DJANGO_USE_X_FORWARDED_HOST=true

# Só atualiza se estiver na main e sem alterações locais (não atropela trabalho em andamento).
if [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] && git diff --quiet && git diff --cached --quiet; then
  git pull -q --ff-only origin main && echo "Código atualizado: $(git log --oneline -1)"
  pip install -q --user -r requirements.txt
else
  echo "Branch diferente da main ou alterações locais: código não foi atualizado automaticamente."
fi

python manage.py migrate --noinput -v0

# Completa o conteúdo de demonstração que faltar (imagens, banners, páginas). Não sobrescreve edições.
HOSTS=(--host localhost)
if [ -n "${CODESPACE_NAME:-}" ]; then
  HOSTS+=(--host "${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}")
fi
python manage.py criar_demo "${HOSTS[@]}"

pkill -f "manage.py runserver" 2>/dev/null; sleep 1
nohup python manage.py runserver 0.0.0.0:8000 > /tmp/portal.log 2>&1 &

echo ""
echo "Portal: aba PORTAS → porta 8000."
echo "Painel: mesmo endereço + /admin/"
echo "Log do servidor: /tmp/portal.log"
