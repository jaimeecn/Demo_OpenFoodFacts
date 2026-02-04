import os
import django
import requests
import time
from decimal import Decimal
import sys

# SETUP DJANGO
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qome_backend.settings')
django.setup()

from core.models import Supermercado, IngredienteBase, ProductoReal

# --- CONFIGURACIÓN ---
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; QomeBot/1.0)'}
API_ROOT = "https://tienda.mercadona.es/api/categories/?lang=es"

# 1. DICCIONARIO DE SINÓNIMOS (Lógica OR: Basta con que aparezca UNA palabra)
# Ejemplo: Si dice "Macarrones", nos vale "Plumas" O "Penne" O "Macarrón".
MATCH_SINONIMOS_OR = {
    "Macarrones": ["macarrón", "plumas", "penne", "tiburón", "hélices"],
    "Espaguetis": ["spaghetti", "espagueti", "tallarín"],
    "Arroz": ["arroz"],
    "Gambas": ["gamba", "langostino", "camarón"],
    "Salmón": ["salmón"],
    "Merluza": ["merluza"],
    "Bacalao": ["bacalao"],
    "Atún Lata": ["atún", "bonito"],
    "Lentejas Bote": ["lenteja"],
    "Garbanzos Bote": ["garbanzo"],
    "Pan Molde": ["molde"], # Cualquier pan que diga "molde"
    "Huevo Duro": ["cocido"], # Huevos cocidos
    "Quesitos": ["porciones"],
    "Leche Entera": ["entera"],
    "Leche Semidesnatada": ["semi"],
    "Ajo": ["ajo"],
    "Cebolla": ["cebolla"],
    "Patata": ["patata"],
    "Zanahoria": ["zanahoria"],
    "Pimiento Rojo": ["rojo"],
    "Pimiento Verde": ["verde"],
    "Plátano": ["plátano", "banana"],
    "Manzana": ["manzana"],
    "Naranja": ["naranja"],
    "Limón": ["limón"],
    "Aguacate": ["aguacate"],
    "Tomate": ["tomate"],
    "Lechuga": ["lechuga"],
    "Espinacas": ["espinaca"],
    "Champiñones": ["champiñón"],
    "Pepino": ["pepino"],
    "Berenjena": ["berenjena"],
    "Brócoli": ["brócoli"],
    "Bacon": ["bacon", "panceta"],
    "Salchichas": ["salchicha"],
    "Sal": ["sal"],
    "Azúcar": ["azúcar"],
    "Harina Trigo": ["harina"],
    "Mantequilla": ["mantequilla"],
    "Mozzarella": ["mozzarella"],
    "Queso Rallado": ["rallado", "fundir"],
    "Pan Integral": ["integral"],
    "Mayonesa": ["mayonesa"],
    "Ketchup": ["ketchup"],
    "Café": ["café"],
    "Maíz Dulce": ["maíz"],
    "Orégano": ["orégano"],
    "Pimentón": ["pimentón"],
    "Pimienta": ["pimienta"],
    "Canela": ["canela"],
    "Comino": ["comino"]
}

# 2. DICCIONARIO COMPUESTO (Lógica AND: Deben aparecer TODAS las palabras)
# Ejemplo: "Aceite Oliva" -> Debe tener "Aceite" Y TAMBIÉN "Oliva".
MATCH_COMPUESTO_AND = {
    "Aceite Oliva": ["aceite", "oliva"],
    "Aceite Girasol": ["aceite", "girasol"],
    "Carne Picada Vacuno": ["picada", "vacuno"],
    "Pechuga de Pollo": ["pechuga", "pollo"],
    "Lomo de Cerdo": ["lomo", "cerdo"],
    "Jamón York": ["jamón", "cocido"],
    "Jamón Serrano": ["jamón", "serrano"],
    "Tomate Frito": ["tomate", "frito"],
    "Pan Hamburguesa": ["pan", "burger"],
    "Yogur Natural": ["yogur", "natural"],
    "Yogur Griego": ["yogur", "griego"],
    "Queso Batido": ["queso", "batido"],
    "Queso Fresco": ["queso", "fresco"],
    "Nata Cocinar": ["nata", "cocinar"],
    "Pavo en Lonchas": ["pavo", "lonchas"] # O pechuga pavo
}

def normalizar(texto):
    replacements = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"))
    texto = texto.lower()
    for a, b in replacements:
        texto = texto.replace(a, b)
    return texto

def cumple_criterios_dual(nombre_producto, nombre_ingrediente_base):
    nombre_prod = normalizar(nombre_producto)
    nombre_ing = nombre_ingrediente_base # Usamos la clave original del diccionario

    # 1. INTENTO OR (Sinónimos)
    if nombre_ing in MATCH_SINONIMOS_OR:
        keywords = MATCH_SINONIMOS_OR[nombre_ing]
        # Si ALGUNA keyword está en el nombre, es match
        for k in keywords:
            if normalizar(k) in nombre_prod:
                return True
        return False # Si está en la lista OR pero no matchea ninguna, es false

    # 2. INTENTO AND (Compuestos)
    if nombre_ing in MATCH_COMPUESTO_AND:
        keywords = MATCH_COMPUESTO_AND[nombre_ing]
        # TODAS las keywords deben estar
        for k in keywords:
            if normalizar(k) not in nombre_prod:
                return False
        return True

    # 3. FALLBACK (Búsqueda Literal simple)
    # Si no está en ningún diccionario, buscamos el nombre tal cual
    return normalizar(nombre_ing) in nombre_prod

def obtener_arbol_categorias():
    try:
        r = requests.get(API_ROOT, headers=HEADERS)
        return r.json()
    except Exception as e:
        print(f"❌ Error descargando árbol: {e}")
        return []

def extraer_productos_de_categoria(cat_id):
    url = f"https://tienda.mercadona.es/api/categories/{cat_id}/?lang=es"
    try:
        r = requests.get(url, headers=HEADERS)
        data = r.json()
        productos = []
        if 'categories' in data:
            for sub in data['categories']:
                if 'products' in sub: productos.extend(sub['products'])
        elif 'products' in data:
            productos.extend(data['products'])
        return productos
    except:
        return []

def ejecutar_crawler():
    print("🕷️ CRAWLER MERCADONA V6 (DUAL LOGIC)...")
    
    mercadona, _ = Supermercado.objects.get_or_create(nombre="Mercadona", defaults={'color_brand': '#007A3E'})
    ingredientes_db = list(IngredienteBase.objects.all())
    print(f"📚 Cerebro cargado con {len(ingredientes_db)} ingredientes base.")

    arbol = obtener_arbol_categorias()
    categorias_a_visitar = []
    
    def explorar_nodo(nodo):
        if not nodo.get('categories'):
            categorias_a_visitar.append(nodo['id'])
        else:
            for hijo in nodo['categories']:
                explorar_nodo(hijo)
    
    if 'results' in arbol:
        for raiz in arbol['results']:
            explorar_nodo(raiz)
    
    print(f"🌍 Iniciando barrido en {len(categorias_a_visitar)} pasillos...")

    total_guardados = 0
    
    for i, cat_id in enumerate(categorias_a_visitar): 
        if i % 10 == 0: print(f"   ⏳ Pasillo {i}/{len(categorias_a_visitar)}...")
        
        productos_raw = extraer_productos_de_categoria(cat_id)
        
        for p in productos_raw:
            nombre_prod = p['display_name']
            
            # RECORREMOS TODOS LOS INGREDIENTES A VER SI ENCAJA CON ALGUNO
            for ing in ingredientes_db:
                if cumple_criterios_dual(nombre_prod, ing.nombre):
                    try:
                        info = p['price_instructions']
                        precio = Decimal(info['unit_price'])
                        pum = Decimal(info['reference_price'])
                        fmt = info['reference_format']
                        
                        peso_g = 1000
                        if pum > 0:
                            ratio = float(precio) / float(pum)
                            if fmt in ['kg', 'L']: peso_g = int(ratio * 1000)
                            else: peso_g = int(ratio * 1000)

                        ProductoReal.objects.update_or_create(
                            nombre_comercial=nombre_prod,
                            supermercado=mercadona,
                            ingrediente_base=ing,
                            defaults={
                                "precio_actual": precio,
                                "peso_gramos": peso_g,
                                "precio_por_kg": pum if fmt == 'kg' else (precio / Decimal(peso_g/1000) if peso_g > 0 else 0),
                                "imagen_url": p.get('thumbnail', '')
                            }
                        )
                        total_guardados += 1
                        break # Un producto solo puede ser un ingrediente base a la vez (simplificación)
                    except: pass
        
        time.sleep(0.05) # Vamos un poco más rápido ahora

    print(f"\n🏁 BARRIDO V6 COMPLETADO. {total_guardados} productos en la saca.")

if __name__ == "__main__":
    ejecutar_crawler()