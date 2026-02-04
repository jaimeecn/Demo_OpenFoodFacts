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

# Cabecera para ser "educados" con la API
HEADERS_OFF = {
    'User-Agent': 'QomeDemo/1.0 (Student Project; +http://localhost)'
}

def obtener_datos_off(nombre_ingrediente):
    """
    Consulta la API de Open Food Facts con sistema de REINTENTOS.
    """
    url = "https://es.openfoodfacts.org/cgi/search.pl"
    params = {
        'search_terms': nombre_ingrediente,
        'search_simple': 1,
        'action': 'process',
        'json': 1,
        'page_size': 3, 
        'fields': 'product_name,nutriments' 
    }
    
    # SISTEMA DE REINTENTOS (3 intentos max)
    max_intentos = 3
    for intento in range(1, max_intentos + 1):
        try:
            # Aumentamos timeout a 20s
            r = requests.get(url, params=params, headers=HEADERS_OFF, timeout=20)
            
            if r.status_code == 200:
                data = r.json()
                if 'products' in data and len(data['products']) > 0:
                    producto = data['products'][0]
                    nutris = producto.get('nutriments', {})
                    return {
                        'kcal': int(nutris.get('energy-kcal_100g', 0) or 0),
                        'prot': float(nutris.get('proteins_100g', 0) or 0),
                        'gras': float(nutris.get('fat_100g', 0) or 0),
                        'hidr': float(nutris.get('carbohydrates_100g', 0) or 0)
                    }
                return None # Si responde 200 pero no hay productos, no es error de red
                
        except Exception as e:
            # Si es el último intento, imprimimos error
            if intento == max_intentos:
                print(f"      ❌ Error persistente: {e}")
            else:
                # Si falló pero quedan intentos, esperamos un poco
                print(f"      ⚠️ Timeout. Reintentando ({intento}/{max_intentos})...", end="\r")
                time.sleep(2) # Espera 2 segundos antes de reintentar
    
    return None

def sincronizar():
    print("🌍 CONECTANDO CON OPEN FOOD FACTS (Modo Robusto)...")
    
    ingredientes = IngredienteBase.objects.all()
    total = ingredientes.count()
    actualizados = 0
    
    for i, ing in enumerate(ingredientes):
        print(f"   📡 [{i+1}/{total}] {ing.nombre}...", end=" ")
        
        # Limpieza nombre
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
            print("⚠️ Sin datos (0 kcal)")
        
        # Pausa entre ingredientes distintos para no saturar
        time.sleep(1.0)

    print(f"\n📊 Sincronización finalizada. {actualizados}/{total} ingredientes actualizados.")
    
    print("\n🔄 Recalculando Macros de todas las Recetas...")
    recetas = Receta.objects.all()
    for r in recetas:
        r.recalcular_macros()
    print(f"✅ {recetas.count()} Recetas actualizadas con información nutricional real.")

if __name__ == "__main__":
    sincronizar()