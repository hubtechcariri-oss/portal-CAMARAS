"""Configurações do Portal das Câmaras.

Tudo o que muda entre ambientes vem de variáveis de ambiente (ver .env.example).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(nome, padrao=False):
    return os.environ.get(nome, str(padrao)).lower() in ("1", "true", "sim", "yes")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-inseguro-troque-em-producao")
DEBUG = env_bool("DJANGO_DEBUG", True)

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
    "django.contrib.postgres",
    "apps.camaras",
    "apps.legislativo",
    "apps.noticias",
    "apps.transparencia",
    "apps.esic",
    "apps.ouvidoria",
    "apps.conteudo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.camaras.middleware.CamaraMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
