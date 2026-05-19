# 🎟️ Tickets y Reservas

Sistema web de gestión de eventos, reservas y pagos de tickets desarrollado con **Django 4.2** y **PostgreSQL**, desplegado con **Docker Compose**.

## 📋 Tabla de contenidos
- [Descripción general](#descripción-general)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Modelos del dominio](#modelos-del-dominio)
- [Rutas disponibles](#rutas-disponibles)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Variables de entorno](#variables-de-entorno)
- [Despliegue](docs/DEPLOYMENT.md)
- [Flujo de autenticación](#flujo-de-autenticación)
- [Panel de administración](#panel-de-administración)
- [Autor](#autor)

---

## Descripción general
La aplicación permite a usuarios finales explorar eventos disponibles, realizar reservas de tickets y consultar el historial de sus reservas. Los administradores gestionan toda la información desde un panel dedicado separado de la vista del usuario final.

Las dos secciones principales son:
1. **Sección pública / usuario final** — exploración de eventos, detalle de evento, creación y cancelación de reservas.
2. **Sección de administración** — gestión completa de eventos, lugares, categorías, tickets, reservas y pagos desde `/admin/`.

---

## Tecnologías utilizadas

| Tecnología | Versión | Rol |
| :--- | :--- | :--- |
| **Python** | 3.11 | Lenguaje base |
| **Django** | 4.2.29 | Framework web |
| **PostgreSQL** | 15 | Base de datos relacional |
| **psycopg2-binary** | 2.9.11 | Adaptador PostgreSQL para Django |
| **Pillow** | 10.4.0 | Manejo de imágenes (campo ImageField) |
| **reportlab** | 4.2.5 | Generación de tickets en PDF |
| **qrcode[pil]** | 7.4.2 | Generación de códigos QR (pendiente) |
| **Docker / Docker Compose** | — | Contenedores y orquestación |

---

## Estructura del proyecto

```text
Tickets/
├── config/                  # Configuración central del proyecto
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── usuarios/            # Perfil extendido del usuario
│   │   ├── models.py
│   │   ├── signals.py       # Auto-creación de Perfil al registrar User
│   │   └── apps.py
│   ├── eventos/             # Eventos, lugares, categorías y tipos de ticket
│   │   ├── models.py
│   │   ├── services.py      # Consultas con select_related/prefetch
│   │   ├── views.py
│   │   └── urls.py
│   ├── reservas/            # Reservas y tickets generados
│   │   ├── models.py
│   │   ├── services.py      # Lógica atómica: crear/cancelar/confirmar
│   │   ├── ticket_generator.py  # TicketGenerator ABC + UUID/QR
│   │   ├── pdf.py               # PDF de resumen de reserva
│   │   ├── views.py
│   │   ├── forms.py
│   │   └── tests.py         # Pruebas unitarias, vistas y concurrencia
│   └── pagos/               # Registro de pagos y descarga de tickets PDF
│       ├── models.py
│       ├── services.py      # procesar_pago @transaction.atomic
│       ├── pdf.py           # PDF por ticket con QR
│       ├── views.py
│       └── urls.py
├── templates/
│   ├── base.html            # Plantilla base con navbar y mensajes
│   ├── auth/
│   │   └── login.html
│   ├── eventos/
│   │   ├── home.html
│   │   └── detalle_evento.html
│   └── reservas/
│       ├── mis_reservas.html
│       └── crear_reserva.html
├── dockerfile
├── docker-compose.yml
├── manage.py
└── requirements.txt
```

---

## Modelos del dominio

### `apps.usuarios`
| Modelo | Campos principales |
| :--- | :--- |
| **Perfil** | `user` (OneToOne → User), `telefono`, `documento` |
> [!NOTE]
> El Perfil se crea automáticamente vía señal `post_save` cada vez que se registra un nuevo `User`.

### `apps.eventos`
| Modelo | Campos principales |
| :--- | :--- |
| **CategoriaEvento** | `nombre`, `descripcion` |
| **Lugar** | `nombre`, `direccion`, `ciudad`, `capacidad` |
| **Evento** | `nombre`, `descripcion`, `fecha`, `hora`, `capacidad_total`, `imagen`, `categoria` (FK), `lugar` (FK) |
| **TipoTicket** | `evento` (FK), `nombre`, `precio`, `cantidad_disponible` |

### `apps.reservas`
| Modelo | Campos principales |
| :--- | :--- |
| **Reserva** | `usuario` (FK → User), `evento` (FK), `tipo_ticket` (FK), `cantidad`, `fecha_reserva`, `estado` |
| **Ticket** | `reserva` (FK), `codigo`, `precio_final`, `usado` |
*   **Estados de Reserva:** `pendiente` · `confirmada` · `cancelada`

### `apps.pagos`
| Modelo | Campos principales |
| :--- | :--- |
| **Pago** | `reserva` (OneToOne), `metodo`, `monto`, `estado`, `referencia`, `fecha_pago` |
*   **Métodos de pago:** `tarjeta` · `pse` · `efectivo`
*   **Estados de pago:** `pendiente` · `aprobado` · `rechazado`

---

## Rutas disponibles

| Método | URL | Nombre | Acceso | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/` | `home` | Público | Lista de eventos disponibles |
| GET | `/eventos/` | `catalogo_eventos` | Público | Catálogo con filtros y paginación |
| GET | `/evento/<id>/` | `detalle_evento` | Público | Detalle de un evento y sus tipos de ticket |
| GET/POST | `/accounts/login/` | `login` | Público | Formulario de inicio de sesión |
| POST | `/accounts/logout/` | `logout` | Autenticado | Cierra sesión y redirige a home |
| GET | `/reservas/mis-reservas/` | `mis_reservas` | Autenticado | Lista de reservas del usuario |
| GET/POST | `/reservas/crear/<evento_id>/` | `crear_reserva` | Autenticado | Formulario para crear una reserva |
| POST | `/reservas/cancelar/<reserva_id>/` | `cancelar_reserva` | Autenticado | Cancela una reserva pendiente |
| GET/POST | `/pagos/pagar/<reserva_id>/` | `pagar` | Autenticado | Formulario de pago |
| GET | `/pagos/exitoso/<reserva_id>/` | `pago_exitoso` | Autenticado | Confirmación de pago exitoso |
| GET | `/pagos/ticket/<ticket_id>/pdf/` | `descargar_ticket` | Autenticado | Descarga el ticket en PDF |
| GET | `/admin/` | — | Staff | Panel de administración |

---

## Instalación y ejecución

### Requisitos previos
*   Docker y Docker Compose instalados.

### Pasos
1.  **Clonar el repositorio**
    ```bash
    git clone <url-del-repositorio>
    cd Tickets
    ```
2.  **Levantar los contenedores**
    ```bash
    docker compose up --build -d
    ```
3.  **Aplicar migraciones**
    ```bash
    docker compose exec web python manage.py migrate
    ```
4.  **Cargar datos de prueba (Seed SQL)**
    El archivo `seed_datos_postgres.sql` contiene datos iniciales (categorías, lugares, eventos, tickets y usuario de prueba).
    ```bash
    docker compose exec -T db psql -U postgres -d ticketsdb < seed_datos_postgres.sql
    ```
5.  **Compilar traducciones** (necesario para el selector de idioma)
    ```bash
    docker compose exec web python manage.py compilemessages
    ```
6.  **Ejecutar los tests**
    ```bash
    docker compose exec web python manage.py test
    ```
7.  **Crear superusuario** (Opcional)
    ```bash
    docker compose exec web python manage.py createsuperuser
    ```
8.  **Acceder a la aplicación**
    | URL | Descripción |
    | :--- | :--- |
    | http://localhost:8000/ | Aplicación principal |
    | http://localhost:8000/admin/ | Panel de administración |

    **Usuario demo:**
    - Usuario: `cliente_demo` / Contraseña: `1234`

---

## Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores. Para desarrollo local los valores por defecto funcionan directamente con Docker.

| Variable | Valor por defecto | Descripción |
| :--- | :--- | :--- |
| **SECRET_KEY** | (generada) | Clave secreta de Django |
| **DEBUG** | `True` | Modo depuración (usar `False` en producción) |
| **ALLOWED_HOSTS** | `localhost,127.0.0.1` | Hosts permitidos |
| **DB_NAME** | `ticketsdb` | Nombre de la base de datos |
| **DB_USER** | `postgres` | Usuario de PostgreSQL |
| **DB_PASSWORD** | `postgres` | Contraseña de PostgreSQL |
| **DB_HOST** | `db` | Host del servicio de base de datos |
| **DB_PORT** | `5432` | Puerto de PostgreSQL |
| **EMAIL_BACKEND** | `console.EmailBackend` | Backend de correo (`console` en dev, `smtp.EmailBackend` en prod) |
| **EMAIL_HOST** | _(vacío)_ | Servidor SMTP (ej. `smtp.gmail.com`, `smtp.mailtrap.io`) |
| **EMAIL_PORT** | `587` | Puerto SMTP (587 para TLS, 465 para SSL) |
| **EMAIL_USE_TLS** | `True` | Activar TLS en la conexión SMTP |
| **EMAIL_HOST_USER** | _(vacío)_ | Usuario/dirección del remitente SMTP |
| **EMAIL_HOST_PASSWORD** | _(vacío)_ | Contraseña o App Password del remitente |
| **DEFAULT_FROM_EMAIL** | `noreply@vibepas.com` | Dirección "De:" en los correos enviados |

> [!WARNING]
> En producción establece una `SECRET_KEY` segura, `DEBUG=False` y configura `ALLOWED_HOSTS` con tu dominio real.
> Con `DEBUG=False` Django renderiza las plantillas `templates/404.html` y `templates/500.html` personalizadas.

---

## Configuración de correo (SMTP)

El sistema envía dos tipos de correo automáticamente:
- **Confirmación de reserva** — al completar el pago exitosamente (`apps/pagos/services.py`)
- **Cancelación de reserva** — al cancelar una reserva (`apps/reservas/services.py`)

### Desarrollo (consola)

Por defecto los correos se imprimen en la consola del servidor. No requiere configuración adicional.

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Producción con Gmail

1. Activa la verificación en dos pasos en tu cuenta Google.
2. Genera una **App Password** en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
3. Configura en tu `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password-de-16-chars
DEFAULT_FROM_EMAIL=noreply@vibepas.com
```

### Producción con Mailtrap (pruebas)

Mailtrap permite capturar correos en staging sin enviarlos realmente. Obtén las credenciales en tu bandeja Mailtrap:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mailtrap.io
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<mailtrap-user>
EMAIL_HOST_PASSWORD=<mailtrap-password>
DEFAULT_FROM_EMAIL=noreply@vibepas.com
```

> [!NOTE]
> Las plantillas de correo se encuentran en `templates/emails/`:
> - `reserva_confirmada.html` / `reserva_confirmada.txt`
> - `reserva_cancelada.html` / `reserva_cancelada.txt`

---

## Flujo de autenticación

**Usuario no autenticado**
- `/accounts/login/` ──► credenciales válidas ──► redirige a `/` (home)
- Vista protegida ──► redirige automáticamente a login (`LOGIN_URL = 'login'`)

**Usuario autenticado**
- Puede ver: `home`, `detalle de evento`
- Puede usar: `mis reservas`, `crear reserva`, `cancelar reserva`
- `POST /accounts/logout/` ──► redirige a `/` (home)

Las vistas privadas usan el decorador `@login_required`. Si un usuario no autenticado intenta acceder, Django lo redirige a `/accounts/login/` automáticamente.

---

## Panel de administración
Accesible en `/admin/` únicamente para usuarios con `is_staff = True`.

| Modelo | Buscar por | Filtrar por |
| :--- | :--- | :--- |
| **Evento** | `nombre` | `categoría`, `fecha` |
| **TipoTicket** | — | `evento` |
| **Lugar** | `nombre`, `ciudad` | — |
| **CategoriaEvento** | `nombre` | — |
| **Reserva** | `usuario`, `evento` | `estado`, `evento` |
| **Ticket** | `código` | `usado` |
| **Pago** | `referencia` | `estado`, `método` |
| **Perfil** | `usuario`, `documento` | — |

---

## Autores
**Thomas Osorio**
**Juan Jose Baron**
**Emmanuel Hernandez**
Proyecto académico — Sistema de Tickets y Reservas
Django 4.2 · PostgreSQL 15 · Docker
