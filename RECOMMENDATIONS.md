Resumen de recomendaciones y pasos accionables

Prioridad Alta
- Evitar N+1 en admin y vistas: usar `select_related` y `prefetch_related` (ya aplicado en `ReservationAdmin`). Revisar otras vistas y APIs.
- Mover llamadas a GraphQL y lógica pesada desde `signals` y acciones del admin a tareas asíncronas (Celery/RQ). Añadir reintentos y timeouts en las peticiones HTTP.
- Añadir índices en columnas frecuentemente filtradas (`Menu.date`, `Reservation.person`, `Reservation.menu`, `Reservation.reservation_category`) (ya aplicado).
- Configurar caching para consultas de menús/horarios y resultados de GraphQL (Redis).

Prioridad Media
- Optimizar `JSONField`: si se realizan consultas sobre su contenido, usar Postgres `JSONB` y GIN indexes o normalizar en tablas relacionales.
- Paginación y límites por defecto en los listados y endpoints.
- Pool de conexiones y `CONN_MAX_AGE` para reducir overhead en DB.

Prioridad Baja
- Eliminar duplicados de assets (varias versiones de jQuery). Minificar y servir por CDN o con `collectstatic` + servidor estático.
- Habilitar HSTS, cookies seguras y revisar `USE_TZ=True` en producción.

Operacional / DevOps
- Añadir `requirements.txt` y pipeline CI (tests, lint). Añadir `Dockerfile` y `docker-compose` para entorno reproducible.
- Integrar Sentry o similar para monitoreo de errores.

Pasos concretos sugeridos
1. Levantar el entorno en Docker (Postgres + Redis) y ejecutar tests.
2. Implementar Celery y mover la lógica del `post_save` de `Menu` y `post_delete` de `ReservCatSchedule` a tareas.
3. Medir con `django-debug-toolbar`/`django-silk` y optimizar consultas lentas.
4. Añadir migraciones para índices y desplegar en staging.

Si quieres, puedo crear PRs separados para: (A) CI + requirements, (B) Docker + Celery example, (C) refactor de signals a tareas.
