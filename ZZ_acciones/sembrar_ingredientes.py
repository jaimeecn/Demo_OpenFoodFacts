import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qome_backend.settings')
django.setup()

from core.models import IngredienteBase

def sembrar():
    print("🌱 Sembrando Despensa Maestra COMPLETA (V5)...")
    
    lista = [
        # --- NUEVOS AÑADIDOS PARA RECETAS AVANZADAS ---
        ('Guisantes', 'Verdura'), ('Jamón York', 'Carniceria'), 
        ('Perejil', 'Verdura'), ('Pan Hamburguesa', 'Despensa'),
        ('Quesitos', 'Lacteos'), ('Huevo Duro', 'Huevos'), # Se buscará como huevo cocido o normal
        ('Pan Molde', 'Despensa'), ('Harina Trigo', 'Despensa'),
        ('Gambas', 'Pescaderia'), ('Espaguetis', 'Despensa'),
        ('Lentejas Bote', 'Despensa'), ('Garbanzos Bote', 'Despensa'),
        ('Macarrones', 'Despensa'),
        
        # --- CARNICERÍA ---
        ('Pechuga de Pollo', 'Carniceria'), ('Carne Picada Vacuno', 'Carniceria'), 
        ('Lomo de Cerdo', 'Carniceria'), ('Jamón Serrano', 'Carniceria'),
        ('Pavo en Lonchas', 'Carniceria'), ('Salchichas', 'Carniceria'),
        ('Bacon', 'Carniceria'), ('Conejo', 'Carniceria'),

        # --- PESCADERÍA ---
        ('Salmón', 'Pescaderia'), ('Merluza', 'Pescaderia'), 
        ('Atún Lata', 'Pescaderia'), ('Bacalao', 'Pescaderia'),
        ('Sepia', 'Pescaderia'), ('Dorada', 'Pescaderia'),

        # --- FRUTA Y VERDURA ---
        ('Plátano', 'Fruta'), ('Manzana', 'Fruta'), ('Naranja', 'Fruta'), 
        ('Fresas', 'Fruta'), ('Limón', 'Fruta'), ('Aguacate', 'Verdura'),
        ('Lechuga', 'Verdura'), ('Tomate', 'Verdura'), ('Cebolla', 'Verdura'),
        ('Ajo', 'Verdura'), ('Pimiento Rojo', 'Verdura'), ('Pimiento Verde', 'Verdura'),
        ('Calabacín', 'Verdura'), ('Zanahoria', 'Verdura'), ('Espinacas', 'Verdura'),
        ('Patata', 'Verdura'), ('Champiñones', 'Verdura'), ('Brócoli', 'Verdura'),
        ('Pepino', 'Verdura'), ('Berenjena', 'Verdura'),

        # --- LÁCTEOS Y HUEVOS ---
        ('Leche Entera', 'Lacteos'), ('Leche Semidesnatada', 'Lacteos'), 
        ('Yogur Natural', 'Lacteos'), ('Yogur Griego', 'Lacteos'), ('Queso Batido', 'Lacteos'),
        ('Mozzarella', 'Lacteos'), ('Queso Rallado', 'Lacteos'), ('Mantequilla', 'Lacteos'),
        ('Huevos', 'Huevos'), ('Nata Cocinar', 'Lacteos'), ('Queso Fresco', 'Lacteos'),

        # --- DESPENSA BÁSICA ---
        ('Arroz', 'Despensa'), ('Pan Integral', 'Despensa'), ('Avena', 'Despensa'),
        ('Azúcar', 'Despensa'), ('Sal', 'Despensa'),
        ('Aceite Oliva', 'Despensa'), ('Aceite Girasol', 'Despensa'), ('Vinagre', 'Despensa'),
        ('Tomate Frito', 'Despensa'), ('Mayonesa', 'Despensa'), ('Ketchup', 'Despensa'),
        ('Café', 'Despensa'), ('Cacao Polvo', 'Despensa'), ('Maíz Dulce', 'Despensa'),
        
        # --- ESPECIAS ---
        ('Orégano', 'Despensa'), ('Pimentón', 'Despensa'), ('Pimienta', 'Despensa'),
        ('Canela', 'Despensa'), ('Comino', 'Despensa')
    ]

    count = 0
    for nombre, cat in lista:
        obj, created = IngredienteBase.objects.get_or_create(
            nombre=nombre,
            defaults={'categoria': cat}
        )
        if created: count += 1

    print(f"✅ {count} nuevos ingredientes añadidos. Total en BD: {IngredienteBase.objects.count()}")

if __name__ == "__main__":
    sembrar()