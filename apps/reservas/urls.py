# Autor: Thomas Osorio

from django.urls import path
from . import views

urlpatterns = [
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('crear/<int:evento_id>/', views.crear_reserva, name='crear_reserva'),
    path('cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('confirmacion/<int:reserva_id>/', views.confirmacion_reserva, name='confirmacion_reserva'),
    path('descargar/<int:reserva_id>/', views.descargar_ticket_pdf, name='descargar_reserva_ticket'),
]
