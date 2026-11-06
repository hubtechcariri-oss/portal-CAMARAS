"""Configurações do Portal das Câmaras.

Tudo o que muda entre ambientes vem de variáveis de ambiente (ver .env.example).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(nome, padrao=False):
    return os.environ.get(nome, str(padrao)).lower() in ("1", "true", "sim", "yes")


DEBUG = env_bool("DJANGO_DEBUG", True)


def _chave_secreta():
    """DJANGO_SECRET_KEY, ou uma chave gerada uma vez e guardada em .chave_secreta (hospedagens sem
    painel de variáveis seguro). Em desenvolvimento, uma chave fixa basta."""
    if os.environ.get("DJANGO_SECRET_KEY"):
        return os.environ["DJANGO_SECRET_KEY"]
    if DEBUG:
        return "dev-inseguro-troque-em-producao"
    arquivo = BASE_DIR / ".chave_secreta"
    if not arquivo.exists():
        from django.core.management.utils import get_random_secret_key

        arquivo.write_text(get_random_secret_key())
        arquivo.chmod(0o600)
    return arquivo.read_text().strip()


SECRET_KEY = _chave_secreta()

# Os domínios válidos são validados pelo middleware de câmara (tabela Dominio).
# Em produção, mantenha "*" apenas atrás de um proxy/CDN que filtre o Host.
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Atrás de um proxy (Codespaces, CDN), o domínio original chega em X-Forwarded-Host.
# Só ative quando o proxy for confiável e sobrescrever esse cabeçalho.
USE_X_FORWARDED_HOST = env_bool("DJANGO_USE_X_FORWARDED_HOST", False)

# Origens HTTPS aceitas em formulários (ex.: "https://*.app.github.dev").
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.camaras",
    "apps.legislativo",
    "apps.noticias",
    "apps.transparencia",
    "apps.esic",
    "apps.ouvidoria",
    "apps.conteudo",
    "apps.integracoes",
]

# Banco: PostgreSQL (padrão) ou MySQL/MariaDB (hospedagens compartilhadas). Ver docs/hospedagem-compartilhada.md.
DB_ENGINE = os.environ.get("DB_ENGINE", "postgresql")
if DB_ENGINE == "postgresql":
    INSTALLED_APPS.insert(INSTALLED_APPS.index("django.contrib.staticfiles") + 1, "django.contrib.postgres")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve /static/ sem precisar de nginx/Apache configurado
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.camaras.middleware.CamaraMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.camaras.auditoria.AuditoriaMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.camaras.context_processors.camara",
                "apps.conteudo.context_processors.menu",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if DB_ENGINE == "mysql":
    import pymysql

    pymysql.version_info = (2, 2, 1, "final", 0)  # o Django pede mysqlclient >= 2.2.1; o PyMySQL é compatível
    pymysql.install_as_MySQLdb()
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "portal"),
            "USER": os.environ.get("DB_USER", "portal"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
            "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"},
            # Grava no horário de Brasília: assim o MySQL não precisa das tabelas de fuso (CONVERT_TZ),
            # que hospedagens compartilhadas costumam não ter. O Brasil não tem horário de verão desde 2019.
            "TIME_ZONE": "America/Sao_Paulo",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "portal"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
# Em hospedagem compartilhada não há servidor web configurável: o próprio Django entrega /media/.
SERVIR_MEDIA = env_bool("DJANGO_SERVIR_MEDIA", False)

# Anexos de e-SIC e Ouvidoria podem conter dados pessoais: ficam fora do MEDIA_ROOT
# (que é público) e só são entregues por views que checam permissão.
ANEXOS_ROOT = Path(os.environ.get("ANEXOS_ROOT", BASE_DIR / "anexos_privados"))
ANEXOS_TAMANHO_MAXIMO_MB = 10
ANEXOS_EXTENSOES = ["pdf", "jpg", "jpeg", "png", "doc", "docx", "odt", "xls", "xlsx", "ods", "txt", "csv"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Prazos do e-SIC (LAI, art. 11): 20 dias, prorrogáveis por mais 10.
ESIC_PRAZO_DIAS = 20
ESIC_PRORROGACAO_DIAS = 10

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Prazos da Ouvidoria (Lei 13.460/2017, art. 16): 30 dias, prorrogáveis uma vez por mais 30.
OUVIDORIA_PRAZO_DIAS = 30
OUVIDORIA_PRORROGACAO_DIAS = 30
