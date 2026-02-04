import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qome_backend.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import PerfilUsuario, Supermercado

def setup_admin():
    print("⚙️ Configurando Perfil de Admin...")
    
    # 1. Asegurar Usuario y Perfil
    user, _ = User.objects.get_or_create(username="admin")
    if not user.check_password("admin"): user.set_password("admin"); user.save()
    
    perfil, created = PerfilUsuario.objects.get_or_create(usuario=user)
    
    # 2. Asignar Mercadona
    mercadona = Supermercado.objects.filter(nombre="Mercadona").first()
    if mercadona:
        perfil.supermercados_seleccionados.add(mercadona)
        print("✅ Mercadona asignado a 'admin'.")
    else:
        print("❌ No se encontró Mercadona. Ejecuta el scraper primero.")

    perfil.save()

if __name__ == "__main__":
    setup_admin()