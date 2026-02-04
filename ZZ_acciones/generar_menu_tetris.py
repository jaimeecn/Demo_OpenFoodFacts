import os
import django
import sys
import json 
import random
from datetime import date, timedelta
from django.db.models import Min, Q

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qome_backend.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Receta, PlanSemanal, ComidaPlanificada, ProductoReal, CostePorSupermercado

def generar_tetris(usuario_nombre="admin"):
    print(f"🧩 Tetris V8 (Logística Real): Generando plan para '{usuario_nombre}'...")
    
    try:
        user = User.objects.get(username=usuario_nombre)
        perfil = user.perfil
    except User.DoesNotExist:
        print(f"❌ Usuario '{usuario_nombre}' no encontrado.")
        return
    except:
        print(f"❌ El usuario '{usuario_nombre}' no tiene perfil creado.")
        return

    # 1. OBTENER SUPERMERCADOS DEL USUARIO
    mis_supers = perfil.supermercados_seleccionados.all()
    if not mis_supers.exists():
        print("⚠️ ALERTA: El usuario no ha seleccionado supermercados. Usando TODOS por defecto.")
        # Fallback para evitar crash si el usuario es nuevo
        from core.models import Supermercado
        mis_supers = Supermercado.objects.all()
    else:
        print(f"🛒 Supermercados activos: {[s.nombre for s in mis_supers]}")

    # 2. LIMPIEZA
    lunes_proximo = date.today() + timedelta(days=(7 - date.today().weekday()))
    plan, _ = PlanSemanal.objects.get_or_create(usuario=user, fecha_inicio=lunes_proximo)
    plan.comidas.all().delete()
    
    despensa = {} 
    cesta_compra_real = {}
    memoria_reciente = [] 
    LIMITE_MEMORIA = 5
    coste_total_plan = 0.0

    dias = range(7)
    momentos = ['COMIDA', 'CENA']

    # 3. BUCLE SEMANAL
    for dia in dias:
        for momento in momentos:
            print(f"\n🔎 Día {dia} ({momento})...")
            
            # FILTRADO INTELIGENTE (WHERE coste IN mis_supers)
            # Buscamos recetas que sean "posibles" en AL MENOS UNO de mis supermercados
            # y ordenamos por el coste mínimo disponible para mí.
            candidatas = Receta.objects.filter(
                costes_por_supermercado__supermercado__in=mis_supers,
                costes_por_supermercado__es_posible=True
            ).annotate(
                precio_minimo_mio=Min('costes_por_supermercado__coste')
            ).order_by('precio_minimo_mio') # Las más baratas primero (Estrategia Ahorro)

            # Filtro Anti-Repetición
            if memoria_reciente:
                candidatas = candidatas.exclude(titulo__in=memoria_reciente)

            # Selección (Top 5 más baratas y elegimos una al azar para variar, o la nº1 si somos estrictos)
            # Aquí añadimos un poco de azar entre las baratas para no comer siempre arroz blanco
            pool_barato = candidatas[:10] 
            
            receta_elegida = None
            if pool_barato.exists():
                receta_elegida = random.choice(pool_barato)
            
            if receta_elegida:
                print(f"   🍽️  {receta_elegida.titulo} (Aprox. {receta_elegida.precio_minimo_mio}€)")
                coste_total_plan += float(receta_elegida.precio_minimo_mio)
                
                memoria_reciente.append(receta_elegida.titulo)
                if len(memoria_reciente) > LIMITE_MEMORIA: memoria_reciente.pop(0)

                # --- GENERACIÓN DE LISTA DE COMPRA (ROUTING) ---
                for item in receta_elegida.ingredientes.all():
                    nombre_base = item.ingrediente_base.nombre
                    necesario = item.cantidad_gramos
                    
                    if nombre_base not in despensa:
                        despensa[nombre_base] = {'stock': 0}

                    if despensa[nombre_base]['stock'] < necesario:
                        # BUSCAMOS EL PRODUCTO REAL SOLO EN MIS SUPERMERCADOS
                        candidatos = ProductoReal.objects.filter(
                            ingrediente_base=item.ingrediente_base,
                            supermercado__in=mis_supers
                        ).order_by('precio_por_kg') # El más eficiente

                        prod = candidatos.first()
                        if not prod:
                            print(f"      ⚠️ No encontrado en tus supers: {nombre_base}")
                            continue

                        # Lógica de compra
                        peso_pack = prod.peso_gramos
                        cantidad_a_comprar = 1
                        
                        # Si necesitamos mucho (ej. 500g y pack es de 100g), compramos más
                        deficit = necesario - despensa[nombre_base]['stock']
                        while (cantidad_a_comprar * peso_pack) < deficit:
                            cantidad_a_comprar += 1

                        despensa[nombre_base]['stock'] += (peso_pack * cantidad_a_comprar)
                        
                        # Añadir a cesta visual
                        clave = f"{prod.nombre_comercial} ({prod.supermercado.nombre})"
                        if clave not in cesta_compra_real:
                            cesta_compra_real[clave] = {
                                'super': prod.supermercado.nombre,
                                'unidades': 0,
                                'precio_u': float(prod.precio_actual),
                                'total': 0.0
                            }
                        cesta_compra_real[clave]['unidades'] += cantidad_a_comprar
                        cesta_compra_real[clave]['total'] += (cantidad_a_comprar * float(prod.precio_actual))

                    despensa[nombre_base]['stock'] -= necesario

                ComidaPlanificada.objects.create(plan=plan, receta=receta_elegida, dia_semana=dia, momento=momento)

    # GUARDAR
    plan.lista_compra_generada = json.dumps(cesta_compra_real)
    plan.coste_total_estimado = coste_total_plan
    plan.save()
    print(f"\n✨ Plan Generado. Coste estimado para tus supermercados: {coste_total_plan:.2f}€")

if __name__ == "__main__":
    generar_tetris()