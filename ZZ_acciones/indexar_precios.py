import os
import django
import sys
from decimal import Decimal

# 1. SETUP DJANGO
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qome_backend.settings')
django.setup()

from core.models import Receta, Supermercado, CostePorSupermercado, ProductoReal

def indexar_precios():
    print("📊 INDEXADOR DE PRECIOS V1: Calculando costes por supermercado...")
    
    recetas = Receta.objects.all()
    supers = Supermercado.objects.all()
    
    if not supers.exists():
        print("❌ Error: No hay supermercados creados. Ejecuta primero el scraper.")
        return

    contador_updates = 0

    for receta in recetas:
        print(f"\n🥘 Analizando: {receta.titulo}")
        ingredientes_receta = receta.ingredientes.all()

        for super_obj in supers:
            coste_total = Decimal(0.0)
            es_posible = True
            ingredientes_faltantes = []

            for item in ingredientes_receta:
                base = item.ingrediente_base
                cantidad_necesaria = item.cantidad_gramos

                # Buscamos producto en ESTE supermercado específico
                producto = ProductoReal.objects.filter(
                    ingrediente_base=base, 
                    supermercado=super_obj
                ).order_by('precio_por_kg').first() # El más barato por kg

                if producto and producto.precio_por_kg:
                    # Coste = (PrecioKG / 1000) * GramosNecesarios
                    coste_item = (producto.precio_por_kg / 1000) * Decimal(cantidad_necesaria)
                    coste_total += coste_item
                else:
                    es_posible = False
                    ingredientes_faltantes.append(base.nombre)
            
            # Guardamos o actualizamos el coste
            coste_obj, created = CostePorSupermercado.objects.update_or_create(
                receta=receta,
                supermercado=super_obj,
                defaults={
                    'coste': coste_total,
                    'es_posible': es_posible
                }
            )
            
            estado = f"✅ {coste_total:.2f}€" if es_posible else f"❌ Faltan: {', '.join(ingredientes_faltantes)}"
            print(f"   🏪 {super_obj.nombre}: {estado}")
            contador_updates += 1

    print(f"\n✨ Indexación completada. {contador_updates} registros actualizados.")

if __name__ == "__main__":
    indexar_precios()