from django.db import connection
from django.http import JsonResponse


def health(request):
    """Liveness/readiness probe: 200 if app and DB respond, 503 otherwise."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)
    return JsonResponse({"status": "ok"})
