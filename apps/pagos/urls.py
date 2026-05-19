from django.urls import path
from . import views

urlpatterns = [
    path('pagar/<int:reserva_id>/', views.pagar, name='pagar'),
    path('exitoso/<int:reserva_id>/', views.pago_exitoso, name='pago_exitoso'),
    path('ticket/<int:ticket_id>/pdf/', views.descargar_ticket, name='descargar_ticket'),
]
