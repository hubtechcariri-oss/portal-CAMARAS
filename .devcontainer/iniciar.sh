#!/usr/bin/env bash
# Roda sempre que o Codespace é aberto: sobe o servidor em segundo plano.
if ! pgrep -f "manage.py runserver" >/dev/null; then
  nohup python manage.py runserver 0.0.0.0:8000 > /tmp/portal.log 2>&1 &
fi
echo ""
echo "Portal: aba PORTS → porta 8000 (abre sozinho no navegador)."
echo "Painel: mesmo endereço + /admin/  (usuário: admin, senha: demo123)"
echo "Log do servidor: /tmp/portal.log"
