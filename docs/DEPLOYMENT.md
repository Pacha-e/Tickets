# Despliegue en Render

Guía corta para publicar VIBEPAS con PostgreSQL administrado.

## Preparación local

1. Verifica que no falten migraciones:

   ```bash
   docker compose exec web python manage.py makemigrations --check --dry-run
   docker compose exec web python manage.py migrate
   ```

2. Compila traducciones cuando cambien archivos `.po`:

   ```bash
   docker compose exec web python manage.py compilemessages
   ```

3. Valida estáticos:

   ```bash
   docker compose exec web python manage.py collectstatic --no-input
   ```

4. Corre pruebas:

   ```bash
   docker compose exec web python manage.py test
   ```

## Blueprint

El archivo `render.yaml` crea:

- Servicio web Python `vibepas`
- Base PostgreSQL `vibepas-db`
- `SECRET_KEY` generado por Render
- `DEBUG=False`
- `DATABASE_URL` conectado desde la base
- Disco persistente `vibepas-media` para QRs en `MEDIA_ROOT`

Render usa:

```bash
pip install -r requirements.txt && python manage.py compilemessages && python manage.py collectstatic --no-input
python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

## Variables

Con Blueprint, Render llena `DATABASE_URL`. En despliegues manuales puedes usar `DATABASE_URL` o las variables `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

Variables obligatorias:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `DATABASE_URL` o `DB_*`
- `MEDIA_ROOT` si usas disco persistente para QRs
- `STATIC_ROOT` para salida de `collectstatic`

Variables de seguridad recomendadas en produccion:

- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_HSTS_SECONDS=3600` o mayor
- `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
- `SECURE_HSTS_PRELOAD=True`

## Media y QRs

Los QR de tickets se guardan en `MEDIA_ROOT`. El Blueprint monta un disco persistente en `/opt/render/project/src/media` para que los archivos no se pierdan entre reinicios o redeploys. En despliegues manuales, crea un persistent disk equivalente o configura almacenamiento externo.

Variables SMTP opcionales:

- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`

## Después del primer deploy

1. Crea superusuario:

   ```bash
   python manage.py createsuperuser
   ```

2. Verifica:

   - `/health`
   - `/robots.txt`
   - `/sitemap.xml`
   - `/eventos/`
   - Flujo reserva -> pago -> QR
