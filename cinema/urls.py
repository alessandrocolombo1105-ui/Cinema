from django.urls import path

from . import views

app_name = 'cinema'

urlpatterns = [
    path('', views.home, name='home'),
    path('film/', views.film_detail, name='film_detail'),
]
