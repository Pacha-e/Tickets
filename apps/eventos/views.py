# Autor: Thomas Osorio

from django.views.generic import ListView, DetailView

from . import services
from .models import Evento


class EventoListView(ListView):
    model = Evento
    template_name = 'eventos/catalogo_eventos.html'
    context_object_name = 'eventos'
    ordering = ['fecha']
    paginate_by = 10

    def get_queryset(self):
        return services.get_eventos_disponibles(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = services.get_categorias()

        # Para que la paginación conserve los filtros actuales.
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['pagination_query'] = query_params.urlencode()

        return context


class HomeView(EventoListView):
    """
    Mantiene el nombre `home` por compatibilidad con la navbar.
    """
    template_name = 'eventos/home.html'
    paginate_by = 6


class EventoDetailView(DetailView):
    model = Evento
    template_name = 'eventos/detalle_evento.html'
    context_object_name = 'evento'

    def get_object(self, queryset=None):
        return services.get_evento_detalle(self.kwargs['pk'])
