from django.urls import path
from django.contrib.auth import views as auth_views # <--- Importante para Login/Logout
from . import views

urlpatterns = [
    # RUTAS PRINCIPALES
    path('', views.lista_recetas, name='home'),
    path('receta/<int:receta_id>/', views.detalle_receta, name='detalle_receta'),
    path('mi-plan/', views.ver_plan_semanal, name='plan_semanal'),
    
    # RUTAS DE USUARIO
    path('registro/', views.registro, name='registro'),
    path('perfil/', views.perfil, name='perfil'),

    # RUTAS DE AUTENTICACIÓN (Las que faltaban)
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]