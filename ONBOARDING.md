# VibePas — Guía de Incorporación

> ¿Nuevo en el proyecto? Empieza aquí. Tendrás el entorno corriendo en menos de 10 minutos.

## ¿Qué es VibePas?

Aplicación web en Django 4.2 para gestión de eventos, reservas de entradas y pagos. Proyecto académico con PostgreSQL 15 y Docker Compose.

## Estado del proyecto (mayo 2026)

### Implementado ✅

| Funcionalidad | Ubicación |
|---------------|-----------|
| Catálogo de eventos con filtros (categoría, fecha, nombre) | `apps/eventos/` |
| Reservas con decremento atómico de stock | `apps/reservas/services.py` |
| Procesamiento de pagos (simulado) | `apps/pagos/services.py` |
| Generación de tickets vía DIP (TicketGenerator ABC) | `apps/reservas/ticket_generator.py` |
| Descarga de ticket en PDF (reportlab) | `apps/pagos/views.py → descargar_ticket` |
| Registro de usuarios y login | `apps/usuarios/` |
| Internacionalización español/inglés con selector de idioma | `locale/`, `templates/partials/language_switcher.html` |
| 6 tests unitarios de lógica de negocio | `apps/reservas/tests.py` |
| Diagramas de arquitectura (Mermaid) | `docs/ARCHITECTURE.md` |
| Docker Compose con healthchecks | `docker-compose.yml` |
| Variables de entorno documentadas | `.env.example` |

### Pendiente ❌ (Issues abiertos en GitHub)

| Funcionalidad | Issue |
|---------------|-------|
| Despliegue en la nube (Railway/Render) — 15% de la nota | #10 |
| Compilar archivos .mo para i18n | #11 |
| Generación de tickets con código QR | #12 |
| Páginas de error 404 y 500 personalizadas | #13 |
| Confirmaciones por correo (SMTP) | #14 |
| Cobertura de tests al 80%+ | #16 |
| SEO + robots.txt | #17 |

## Arquitectura

```
Navegador → Vistas Django → Servicios (lógica de negocio) → Modelos → PostgreSQL
                       ↓
               TicketGenerator (ABC)
                ├── UUIDTicketGenerator (pruebas)
                └── QRTicketGenerator (producción)
```

Principio clave: **ninguna lógica de negocio en las vistas**. Las vistas solo gestionan HTTP (formularios, mensajes, redirecciones). Toda la lógica vive en los archivos `services.py`.

Consulta `docs/ARCHITECTURE.md` para los diagramas Mermaid completos.

## Inicio rápido (local)

**Requisito:** Docker Desktop en ejecución.

```bash
# 1. Clonar
git clone https://github.com/thomaszambrano/Tickets
cd Tickets

# 2. Copiar archivo de entorno
cp .env.example .env
# Editar .env si es necesario (los valores por defecto funcionan con Docker local)

# 3. Levantar contenedores
docker compose up --build -d

# 4. Aplicar migraciones
docker compose exec web python manage.py migrate

# 5. Cargar datos de prueba (categorías, lugares, eventos, usuario demo)
docker compose exec -T db psql -U postgres -d ticketsdb < seed_datos_postgres.sql

# 6. Compilar traducciones
docker compose exec web python manage.py compilemessages

# 7. Abrir la aplicación
http://localhost:8000
```

**Usuario demo:** `cliente_demo` / `1234`

**Panel de administración:** http://localhost:8000/admin — requiere crear superusuario primero:
```bash
docker compose exec web python manage.py createsuperuser
```

## Ejecutar tests

```bash
docker compose exec web python manage.py test
```

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `apps/reservas/services.py` | Lógica de reservas (transaccional) |
| `apps/pagos/services.py` | Procesamiento de pagos |
| `apps/reservas/ticket_generator.py` | Generación de tickets vía DIP |
| `apps/reservas/tests.py` | Tests unitarios |
| `config/settings.py` | Configuración Django (dirigida por variables de entorno) |
| `docker-compose.yml` | Infraestructura local |
| `.env.example` | Variables de entorno requeridas |
| `docs/ARCHITECTURE.md` | Diagramas de arquitectura del sistema |
| `seed_datos_postgres.sql` | Datos de demostración |

## Flujo de trabajo Git

```bash
git checkout -b feat/nombre-funcionalidad
# desarrollar...
git commit -m "feat: descripción"
git push origin feat/nombre-funcionalidad
# abrir PR contra main
```

Nomenclatura de ramas: `feat/`, `fix/`, `chore/`, `docs/`

## Solución de problemas

**Conflicto en puerto 5432:** PostgreSQL se expone en el puerto **5433**, no 5432. Si tienes una instancia local de PG, asegúrate de que no esté en el 5433.

**Migraciones desincronizadas:** `docker compose exec web python manage.py migrate`

**El selector de idioma no funciona:** Ejecuta `compilemessages` (paso 6 del inicio rápido).

**El contenedor no arranca:** `docker compose logs web` para ver los errores.
