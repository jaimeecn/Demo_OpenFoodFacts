import os
import django
import requests
import time
import sys

# SETUP
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qome_backend.settings')
django.setup()

from core.models import IngredienteBase, Receta

def obtener_datos_off(nombre_ingrediente):
    """
    Consulta la API de Open Food Facts para obtener macros promedio de un producto.
    """
    url = "https://es.openfoodfacts.org/cgi/search.pl"
    params = {
        'search_terms': nombre_ingrediente,
        'search_simple': 1,
        'action': 'process',
        'json': 1,
        'page_size': 3, # Traemos 3 para filtrar anomalías si fuera necesario
        'fields': 'product_name,nutriments' # Optimizamos la respuesta
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        
        if 'products' in data and len(data['products']) > 0:
            # Cogemos el primer resultado relevante
            # En un sistema real, haríamos una media de los 5 primeros, pero para demo vale el 1º
            producto = data['products'][0]
            nutris = producto.get('nutriments', {})
            
            return {
                'kcal': int(nutris.get('energy-kcal_100g', 0) or 0),
                'prot': float(nutris.get('proteins_100g', 0) or 0),
                'gras': float(nutris.get('fat_100g', 0) or 0),
                'hidr': float(nutris.get('carbohydrates_100g', 0) or 0)
            }
    except Exception as e:
        print(f"   ❌ Error conectando con OFF para '{nombre_ingrediente}': {e}")
    
    return None

def sincronizar():
    print("🌍 CONECTANDO CON OPEN FOOD FACTS (Fuente de Verdad Nutricional)...")
    
    ingredientes = IngredienteBase.objects.all()
    total = ingredientes.count()
    actualizados = 0
    
    for i, ing in enumerate(ingredientes):
        print(f"   📡 Consultando [{i+1}/{total}]: {ing.nombre}...", end=" ")
        
        # Pequeña limpieza para mejorar la búsqueda en OFF
        query = ing.nombre.replace("Bote", "").replace("Lata", "").replace("Fresco", "").strip()
        
        macros = obtener_datos_off(query)
        
        if macros and macros['kcal'] > 0:
            ing.calorias = macros['kcal']
            ing.proteinas = macros['prot']
            ing.grasas = macros['gras']
            ing.hidratos = macros['hidr']
            ing.save()
            print(f"✅ OK ({macros['kcal']} kcal)")
            actualizados += 1
        else:
            print("⚠️ Sin datos (Se mantiene a 0)")
        
        # Respetamos la API de OFF (Rate Limiting ético)
        time.sleep(0.5)

    print(f"\n📊 Sincronización finalizada. {actualizados}/{total} ingredientes actualizados.")
    
    print("\n🔄 Recalculando Macros de todas las Recetas...")
    recetas = Receta.objects.all()
    for r in recetas:
        r.recalcular_macros()
    print(f"✅ {recetas.count()} Recetas actualizadas con información nutricional real.")

if __name__ == "__main__":
    sincronizar()