from django.urls import path

from . import views

app_name = 'cinema'

urlpatterns = [
    path('', views.home, name='home'),
    path('film/', views.film_detail, name='film_detail'),
    path('prenota/<int:screening_id>/', views.booking, name='booking'),
    path('prenota/conferma/', views.booking_success, name='booking_success'),
    path('prenota/conferma/biglietto.ics', views.booking_ticket, name='booking_ticket'),
]
