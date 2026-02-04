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

# --- FILTROS DE SEGURIDAD (BLACKLIST) ---
# Palabras que, si aparecen, DESCARTAN el producto inmediatamente.
BLACKLIST = [
    "perro", "gato", "mascota", "animal", "juniors", "infantil", "bebé", "pañal",
    "champú", "gel", "jabón", "crema", "facial", "corporal", "limpieza", "friegasuelos",
    "detergente", "suavizante", "lejía", "insecticida", "ambientador", "pilas", "bombilla",
    "servilleta", "papel", "higiénico", "toallitas", "discos", "algodón", "bastoncillos",
    "maquillaje", "colonia", "perfume", "desodorante", "estropajo", "bayeta", "fregona",
    "fregaplatos", "lavavajillas", "mopa", "escoba"
]

# 1. DICCIONARIO DE SINÓNIMOS (Lógica OR)
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
    "Pan Molde": ["molde"],
    "Huevo Duro": ["cocido"],
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

# 2. DICCIONARIO COMPUESTO (Lógica AND)
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
    "Pavo en Lonchas": ["pavo", "lonchas"]
}

def normalizar(texto):
    replacements = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"))
    texto = texto.lower()
    for a, b in replacements:
        texto = texto.replace(a, b)
    return texto

def cumple_criterios_seguros(nombre_producto, nombre_ingrediente_base):
    nombre_prod = normalizar(nombre_producto)
    
    # 1. FILTRO BLACKLIST
    for bad in BLACKLIST:
        if bad in nombre_prod: return False

    nombre_ing = nombre_ingrediente_base 

    # 2. INTENTO OR (Sinónimos)
    if nombre_ing in MATCH_SINONIMOS_OR:
        keywords = MATCH_SINONIMOS_OR[nombre_ing]
        for k in keywords:
            kn = normalizar(k)
            # Lógica estricta para palabras cortas (<= 3 letras) como "Sal" o "Ajo"
            if len(kn) <= 3:
                # Debe estar rodeada de espacios o ser inicio/fin de cadena
                if f" {kn} " in f" {nombre_prod} " or nombre_prod.startswith(f"{kn} ") or nombre_prod.endswith(f" {kn}"):
                    return True
            else:
                if kn in nombre_prod: return True
        return False 

    # 3. INTENTO AND (Compuestos)
    if nombre_ing in MATCH_COMPUESTO_AND:
        keywords = MATCH_COMPUESTO_AND[nombre_ing]
        for k in keywords:
            if normalizar(k) not in nombre_prod: return False
        return True

    # 4. FALLBACK
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

def extraer_nutricion(p_data):
    """
    Intenta extraer las kcal por 100g.
    Si no existe o falla, devuelve 0.
    """
    try:
        # Placeholder: Aquí iría la lógica real de parseo del JSON de nutrición
        # Para la demo, si no hay datos claros, 0 es seguro.
        if 'nutrition_information' in p_data:
            return 0 
    except: pass
    return 0

def ejecutar_crawler():
    print("🕷️ CRAWLER MERCADONA V9 (ANTI-BASURA + NUTRICIÓN)...")
    
    mercadona, _ = Supermercado.objects.get_or_create(nombre="Mercadona", defaults={'color_brand': '#007A3E'})
    ingredientes_db = list(IngredienteBase.objects.all())
    
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
    
    print(f"🌍 Escaneando {len(categorias_a_visitar)} pasillos...")

    total_guardados = 0
    
    for i, cat_id in enumerate(categorias_a_visitar): 
        if i % 15 == 0: print(f"   ⏳ Pasillo {i}/{len(categorias_a_visitar)}...")
        
        productos_raw = extraer_productos_de_categoria(cat_id)
        
        for p in productos_raw:
            nombre_prod = p['display_name']
            
            for ing in ingredientes_db:
                # Usamos la nueva función segura
                if cumple_criterios_seguros(nombre_prod, ing.nombre):
                    try:
                        info = p['price_instructions']
                        precio = Decimal(info['unit_price'])
                        pum = Decimal(info['reference_price'])
                        fmt = info['reference_format']
                        
                        peso_g = 1000
                        if pum > 0:
                            ratio = float(precio) / float(pum)
                            # Si la referencia es KG o L, multiplicamos por 1000
                            # Si no, asumimos que es unidad y estimamos
                            if fmt.lower() in ['kg', 'l']: 
                                peso_g = int(ratio * 1000)
                            else:
                                peso_g = int(ratio * 1000)

                        kcal = extraer_nutricion(p)

                        ProductoReal.objects.update_or_create(
                            nombre_comercial=nombre_prod,
                            supermercado=mercadona,
                            ingrediente_base=ing,
                            defaults={
                                "precio_actual": precio,
                                "peso_gramos": peso_g,
                                "precio_por_kg": pum if fmt.lower() in ['kg', 'l'] else (precio / Decimal(peso_g/1000) if peso_g > 0 else 0),
                                "imagen_url": p.get('thumbnail', ''),
                                "kcal_100g": kcal
                            }
                        )
                        total_guardados += 1
                        break 
                    except: pass
        
        time.sleep(0.05)

    print(f"\n🏁 BARRIDO V9 COMPLETADO. {total_guardados} productos limpios.")

if __name__ == "__main__":
    ejecutar_crawler()