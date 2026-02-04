# ARCHIVO: qome_backend/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')), # Esto conecta con el archivo que acabas de crear
]