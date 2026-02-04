import os
import django
import sys
import random

# SETUP
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qome_backend.settings')
django.setup()

from core.models import Receta, IngredienteBase, RecetaIngrediente

def sembrar_recetas_pro():
    print("👨‍🍳 Cocinando Recetario Avanzado (V4 con Utensilios Lógicos)...")

    Receta.objects.all().delete()

    def get_ing(nombre_parcial):
        exacto = IngredienteBase.objects.filter(nombre__iexact=nombre_parcial).first()
        if exacto: return exacto
        parcial = IngredienteBase.objects.filter(nombre__icontains=nombre_parcial).first()
        if parcial: return parcial
        print(f"   ⚠️ Ingrediente no encontrado: '{nombre_parcial}'. Creando dummy...")
        return IngredienteBase.objects.create(nombre=nombre_parcial, categoria='Otros')

    recetas_data = [
        # --- LEGUMBRES Y GUISOS ---
        ("Lentejas Estofadas con Verduras", 40, [
            ('Lentejas Bote', 200), ('Zanahoria', 50), ('Patata', 100), 
            ('Cebolla', 30), ('Ajo', 5), ('Pimentón', 2), ('Aceite Oliva', 10)
        ]),
        ("Garbanzos con Espinacas y Huevo", 25, [
            ('Garbanzos Bote', 200), ('Espinacas', 100), ('Huevos', 60), 
            ('Ajo', 5), ('Aceite Oliva', 10), ('Sal', 2)
        ]),
        ("Salteado de Garbanzos y Pollo", 20, [
            ('Garbanzos Bote', 150), ('Pechuga de Pollo', 100), ('Pimiento Rojo', 30), 
            ('Cebolla', 30), ('Aceite Oliva', 10)
        ]),

        # --- PASTAS Y ARROCES ---
        ("Espaguetis Boloñesa Real", 30, [
            ('Espaguetis', 100), ('Carne Picada Vacuno', 100), ('Tomate Frito', 50), 
            ('Cebolla', 30), ('Orégano', 2), ('Queso Rallado', 15)
        ]),
        ("Macarrones con Atún y Tomate", 20, [
            ('Macarrones', 100), ('Atún Lata', 60), ('Tomate Frito', 60), 
            ('Cebolla', 20), ('Orégano', 1)
        ]),
        ("Arroz Tres Delicias Casero", 25, [
            ('Arroz', 80), ('Huevos', 60), ('Guisantes', 30), 
            ('Jamón York', 30), ('Zanahoria', 20), ('Aceite Oliva', 10), ('Sal', 2)
        ]),
        ("Risotto de Champiñones (Falso)", 35, [
            ('Arroz', 100), ('Champiñones', 100), ('Leche Entera', 50), 
            ('Cebolla', 40), ('Queso Rallado', 20), ('Mantequilla', 10)
        ]),

        # --- CARNES Y AVES ---
        ("Pechuga de Pollo al Limón con Patatas", 30, [
            ('Pechuga de Pollo', 150), ('Patata', 200), ('Limón', 20), 
            ('Ajo', 5), ('Perejil', 2), ('Aceite Oliva', 10)
        ]),
        ("Hamburguesa Casera con Ensalada", 20, [
            ('Carne Picada Vacuno', 150), ('Lechuga', 100), ('Tomate', 100), 
            ('Pan Hamburguesa', 60), ('Ketchup', 10), ('Aceite Oliva', 5)
        ]),
        ("Lomo de Cerdo con Pimientos", 25, [
            ('Lomo de Cerdo', 150), ('Pimiento Rojo', 100), ('Pimiento Verde', 100), 
            ('Cebolla', 50), ('Aceite Oliva', 15), ('Sal', 2)
        ]),

        # --- PESCADOS ---
        ("Salmón a la Plancha con Verduras", 20, [
            ('Salmón', 150), ('Calabacín', 100), ('Berenjena', 100), 
            ('Aceite Oliva', 10), ('Sal', 2)
        ]),
        ("Merluza en Salsa Verde (Básica)", 25, [
            ('Merluza', 150), ('Guisantes', 30), ('Ajo', 5), 
            ('Perejil', 2), ('Harina Trigo', 5), ('Aceite Oliva', 10)
        ]),
        ("Revuelto de Gambas y Ajetes", 15, [
            ('Huevos', 120), ('Gambas', 100), ('Ajo', 10), 
            ('Aceite Oliva', 10), ('Pan Integral', 40)
        ]),

        # --- CENAS LIGERAS ---
        ("Tortilla Francesa con Atún", 10, [
            ('Huevos', 120), ('Atún Lata', 60), ('Lechuga', 100), 
            ('Aceite Oliva', 10), ('Sal', 1)
        ]),
        ("Ensalada César (Versión Qome)", 15, [
            ('Lechuga', 150), ('Pechuga de Pollo', 100), ('Pan Molde', 30), 
            ('Queso Rallado', 20), ('Mayonesa', 15), ('Aceite Oliva', 5)
        ]),
        ("Crema de Calabacín y Queso", 30, [
            ('Calabacín', 300), ('Patata', 100), ('Cebolla', 50), 
            ('Quesitos', 30), ('Aceite Oliva', 10), ('Sal', 2)
        ]),
        ("Sandwich Vegetal Completo", 10, [
            ('Pan Integral', 60), ('Lechuga', 30), ('Tomate', 40), 
            ('Huevo Duro', 60), ('Mayonesa', 10), ('Atún Lata', 30)
        ]),
    ]

    count = 0
    for titulo, tiempo, ingredientes in recetas_data:
        # LÓGICA DE UTENSILIOS (Ya no es random)
        es_horno = "Horno" in titulo or "Asado" in titulo or "Pizza" in titulo or "Pastel" in titulo
        es_sarten = "Sartén" in titulo or "Plancha" in titulo or "Tortilla" in titulo or "Revuelto" in titulo or "Hamburguesa" in titulo or "Salteado" in titulo
        es_tupper = "Lentejas" in titulo or "Garbanzos" in titulo or "Arroz" in titulo or "Pasta" in titulo or "Ensalada" in titulo or "Macarrones" in titulo or "Espaguetis" in titulo or "Crema" in titulo

        receta = Receta.objects.create(
            titulo=titulo,
            tiempo_preparacion=tiempo,
            es_apta_horno=es_horno,
            es_apta_sarten=es_sarten,
            es_apta_tupper=es_tupper,
            # Asumimos que casi todo lo de horno o sartén se puede adaptar a airfryer hoy día
            es_apta_airfryer=(es_horno or es_sarten),
            es_apta_microondas=(es_tupper)
        )

        for nombre_ing, gramos in ingredientes:
            base = get_ing(nombre_ing)
            RecetaIngrediente.objects.create(
                receta=receta,
                ingrediente_base=base,
                cantidad_gramos=gramos
            )
        
        receta.recalcular_macros()
        count += 1
        print(f"   ✅ Creada: {titulo}")

    print(f"\n✨ ¡Hecho! {count} recetas avanzadas listas para indexar.")

if __name__ == "__main__":
    sembrar_recetas_pro()