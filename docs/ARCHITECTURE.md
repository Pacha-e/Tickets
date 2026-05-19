# VibePas - Arquitectura

VibePas es una app Django 4.2 con PostgreSQL. La regla principal del proyecto es
mantener las vistas delgadas: las vistas autentican, cargan objetos y renderizan;
las reglas de negocio viven en `services.py`.

## Capas

```mermaid
graph TD
    subgraph UI["Views + Templates"]
        V_EV[eventos/views.py]
        V_RES[reservas/views.py]
        V_PAG[pagos/views.py]
        V_USU[usuarios/views.py]
        PDF_RES[reservas/pdf.py]
        PDF_PAG[pagos/pdf.py]
    end

    subgraph Services["Business logic"]
        S_EV[eventos/services.py]
        S_RES[reservas/services.py]
        S_PAG[pagos/services.py]
        TG[reservas/ticket_generator.py<br/>TicketGenerator<br/>UUIDTicketGenerator<br/>QRTicketGenerator]
    end

    subgraph Domain["Models"]
        M_EV[eventos/models.py]
        M_RES[reservas/models.py]
        M_PAG[pagos/models.py]
        M_USU[usuarios/models.py]
        SIG[usuarios/signals.py]
    end

    DB[(PostgreSQL)]

    V_EV --> S_EV
    V_RES --> S_RES
    V_PAG --> S_PAG
    V_RES --> PDF_RES
    V_PAG --> PDF_PAG
    S_PAG --> S_RES
    S_RES --> TG
    S_EV --> M_EV
    S_RES --> M_RES
    S_PAG --> M_PAG
    V_USU --> M_USU
    M_USU --> SIG
    M_EV --> DB
    M_RES --> DB
    M_PAG --> DB
    M_USU --> DB
```

## Flujo Reserva + Pago

```mermaid
sequenceDiagram
    actor U as Usuario
    participant RV as reservas.views
    participant RS as reservas.services
    participant PV as pagos.views
    participant PS as pagos.services
    participant TG as QRTicketGenerator
    participant DB as PostgreSQL

    U->>RV: POST /reservas/crear/<evento_id>/
    RV->>RS: crear_reserva(usuario, evento_id, tipo_id, cantidad)
    RS->>DB: SELECT FOR UPDATE TipoTicket
    RS->>DB: UPDATE cantidad_disponible -= cantidad
    RS->>DB: INSERT Reserva pendiente
    RS-->>RV: Reserva

    U->>PV: POST /pagos/pagar/<reserva_id>/
    PV->>PS: procesar_pago(reserva_id, metodo, usuario)
    PS->>DB: SELECT FOR UPDATE Reserva
    PS->>DB: INSERT/UPDATE Pago aprobado
    PS->>RS: confirmar_reserva(reserva)
    RS->>DB: UPDATE Reserva confirmada
    PS->>RS: generar_tickets(reserva)
    RS->>TG: generate(reserva)
    TG->>DB: INSERT Ticket + QR
    PS-->>PV: pago, tickets
    PV-->>U: redirect pago_exitoso
```

## Reglas De Codigo

- Operaciones de inventario y pago usan `@transaction.atomic` y `select_for_update()`.
- Los emails de confirmacion/cancelacion se envian con `transaction.on_commit()`.
- `pagos.signals` no existe: los tickets se generan solo desde `pagos.services`.
- Los PDF viven en `apps/*/pdf.py`, no dentro de las vistas.
- `generar_tickets()` devuelve tickets existentes si la reserva ya los tiene.

## Docker

```mermaid
graph LR
    WEB[web python:3.11-slim :8000]
    DB[(db postgres:15 :5433)]
    WEB -->|service_healthy| DB
    HOST[Host] -->|8000| WEB
    HOST -->|5433| DB
```
