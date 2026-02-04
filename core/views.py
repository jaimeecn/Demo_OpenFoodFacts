import json
import random
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Min, Q
from django.contrib import messages
from .models import (
    Receta, PerfilUsuario, PlanSemanal, Supermercado, 
    ComidaPlanificada, ProductoReal, CostePorSupermercado
)

# --- MOTOR TETRIS V9 (Con Pesos y Macros) ---
def generar_plan_motor(user):
    try:
        perfil = user.perfil
    except:
        return False, "Usuario sin perfil configurado."

    # 1. Supermercados
    mis_supers = perfil.supermercados_seleccionados.all()
    if not mis_supers.exists():
        mis_supers = Supermercado.objects.all()

    # 2. Estrategia Nutricional
    orden_prioridad = 'precio_minimo_mio'
    if perfil.gasto_energetico_diario > 2500:
        orden_prioridad = '-calorias'
    elif perfil.gasto_energetico_diario < 1800:
        orden_prioridad = 'calorias'

    # 3. Limpieza
    inicio_semana = date.today()
    PlanSemanal.objects.filter(usuario=user).delete()
    plan = PlanSemanal.objects.create(usuario=user, fecha_inicio=inicio_semana)
    
    despensa = {} 
    cesta_compra_real = {}
    memoria_reciente = [] 
    coste_total_plan = 0.0

    dias = range(7) 
    momentos = ['COMIDA', 'CENA']

    # 4. Generación
    for dia in dias:
        for momento in momentos:
            # Filtramos recetas posibles
            base_query = Receta.objects.filter(
                costes_por_supermercado__supermercado__in=mis_supers,
                costes_por_supermercado__es_posible=True
            ).annotate(
                precio_minimo_mio=Min('costes_por_supermercado__coste')
            )

            # Ordenamos
            candidatas = base_query.order_by(orden_prioridad, 'precio_minimo_mio')

            # Filtro Anti-Repetición
            if memoria_reciente:
                candidatas = candidatas.exclude(titulo__in=memoria_reciente)

            pool = candidatas[:5]
            if not pool.exists(): continue 
                
            receta_elegida = random.choice(pool)
            
            memoria_reciente.append(receta_elegida.titulo)
            if len(memoria_reciente) > 4: memoria_reciente.pop(0)
            
            coste_plato = receta_elegida.precio_minimo_mio or 0
            coste_total_plan += float(coste_plato)

            # --- GENERAR LISTA DE COMPRA ---
            for item in receta_elegida.ingredientes.all():
                nombre_base = item.ingrediente_base.nombre
                necesario = item.cantidad_gramos
                
                if nombre_base not in despensa: despensa[nombre_base] = 0

                if despensa[nombre_base] < necesario:
                    prod = ProductoReal.objects.filter(
                        ingrediente_base=item.ingrediente_base,
                        supermercado__in=mis_supers
                    ).order_by('precio_por_kg').first()

                    if prod:
                        peso_pack = prod.peso_gramos
                        cantidad_a_comprar = 1
                        deficit = necesario - despensa[nombre_base]
                        
                        while (cantidad_a_comprar * peso_pack) < deficit:
                            cantidad_a_comprar += 1
                        
                        despensa[nombre_base] += (peso_pack * cantidad_a_comprar)
                        
                        clave = f"{prod.nombre_comercial}"
                        if clave not in cesta_compra_real:
                            # FORMATEO DE PESO PARA VISUALIZACIÓN
                            peso_txt = f"{prod.peso_gramos}g"
                            if prod.peso_gramos >= 1000:
                                peso_txt = f"{prod.peso_gramos/1000:.1f}kg".replace(".0kg", "kg")

                            cesta_compra_real[clave] = {
                                'super': prod.supermercado.nombre,
                                'unidades': 0,
                                'precio_u': float(prod.precio_actual),
                                'total': 0.0,
                                'imagen': prod.imagen_url,
                                'peso_display': peso_txt # <--- NUEVO
                            }
                        cesta_compra_real[clave]['unidades'] += cantidad_a_comprar
                        cesta_compra_real[clave]['total'] += (cantidad_a_comprar * float(prod.precio_actual))

                despensa[nombre_base] -= necesario

            ComidaPlanificada.objects.create(
                plan=plan, receta=receta_elegida, dia_semana=dia, momento=momento
            )

    plan.lista_compra_snapshot = json.dumps(cesta_compra_real)
    plan.coste_total_estimado = coste_total_plan
    plan.save()
    
    return True, "Plan generado correctamente."


# --- VISTAS WEB ---

def home(request):
    if request.user.is_authenticated:
        return redirect('plan_semanal')
    else:
        return redirect('login')

def lista_recetas(request):
    recetas = Receta.objects.all()
    perfil = None
    metas = None
    
    if request.user.is_authenticated:
        try:
            perfil = PerfilUsuario.objects.get(usuario=request.user)
            mis_supers = perfil.supermercados_seleccionados.all()

            if mis_supers.exists():
                recetas = recetas.annotate(
                    precio_usuario=Min(
                        'costes_por_supermercado__coste',
                        filter=Q(costes_por_supermercado__supermercado__in=mis_supers)
                    )
                )
            else:
                recetas = recetas.annotate(precio_usuario=Min('costes_por_supermercado__coste'))

            metas = {
                'calorias': perfil.gasto_energetico_diario,
                'proteinas': perfil.objetivo_proteinas,
                'grasas': perfil.objetivo_grasas,
                'hidratos': perfil.objetivo_hidratos,
            }
        except PerfilUsuario.DoesNotExist: pass
    else:
        recetas = recetas.annotate(precio_usuario=Min('costes_por_supermercado__coste'))

    query = request.GET.get('q')
    if query: recetas = recetas.filter(titulo__icontains=query)
    
    # Filtros Utensilios
    if request.GET.get('horno'): recetas = recetas.filter(es_apta_horno=True)
    if request.GET.get('sarten'): recetas = recetas.filter(es_apta_sarten=True)
    if request.GET.get('tupper'): recetas = recetas.filter(es_apta_tupper=True)

    return render(request, 'core/lista_recetas.html', {
        'recetas': recetas, 'perfil': perfil, 'metas': metas
    })

def detalle_receta(request, receta_id):
    receta = get_object_or_404(Receta, id=receta_id)
    costes = receta.costes_por_supermercado.filter(es_posible=True).select_related('supermercado').order_by('coste')
    return render(request, 'core/detalles_receta.html', {'receta': receta, 'costes': costes})

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            PerfilUsuario.objects.create(usuario=user)
            login(request, user)
            return redirect('perfil') 
    else:
        form = UserCreationForm()
    return render(request, 'core/registro.html', {'form': form})

@login_required
def perfil(request):
    perfil_usuario, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
    todos_supers = Supermercado.objects.all()

    if request.method == 'POST':
        perfil_usuario.genero = request.POST.get('genero')
        perfil_usuario.edad = int(request.POST.get('edad') or 30)
        perfil_usuario.altura_cm = int(request.POST.get('altura') or 170)
        perfil_usuario.peso_kg = float(request.POST.get('peso') or 70)
        perfil_usuario.nivel_actividad = request.POST.get('actividad')
        perfil_usuario.objetivo = request.POST.get('objetivo')
        
        presupuesto = request.POST.get('presupuesto')
        if presupuesto: perfil_usuario.presupuesto_semanal = float(presupuesto)
        
        perfil_usuario.tiene_airfryer = 'airfryer' in request.POST
        perfil_usuario.tiene_horno = 'horno' in request.POST
        perfil_usuario.tiene_microondas = 'microondas' in request.POST
        
        supers_ids = request.POST.getlist('supermercados')
        perfil_usuario.supermercados_seleccionados.set(supers_ids)
        
        perfil_usuario.save()
        
        generar_plan_motor(request.user)
        messages.success(request, "Perfil guardado y Plan regenerado.")
        
        return redirect('plan_semanal')

    return render(request, 'core/perfil.html', {
        'perfil': perfil_usuario,
        'supermercados': todos_supers
    })

@login_required
def ver_plan_semanal(request):
    if request.method == 'POST':
        exito, msg = generar_plan_motor(request.user)
        if exito: messages.success(request, msg)
        else: messages.error(request, msg)
        return redirect('plan_semanal')

    plan = PlanSemanal.objects.filter(usuario=request.user).order_by('-fecha_inicio').first()
    
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    calendario = {i: {'nombre': dias_semana[i], 'comida': None, 'cena': None} for i in range(7)}
    lista_compra_visual = {} 
    subtotales_super = {} 

    if plan:
        comidas = plan.comidas.all().select_related('receta')
        for comida in comidas:
            if comida.momento == 'COMIDA':
                calendario[comida.dia_semana]['comida'] = comida.receta
            elif comida.momento == 'CENA':
                calendario[comida.dia_semana]['cena'] = comida.receta
        
        if plan.lista_compra_snapshot:
            try:
                raw_lista = json.loads(plan.lista_compra_snapshot)
                lista_agrupada = {}
                for nombre_prod, datos in raw_lista.items():
                    super_nombre = datos.get('super', 'Otros')
                    if super_nombre not in lista_agrupada: 
                        lista_agrupada[super_nombre] = []
                        subtotales_super[super_nombre] = 0.0
                    
                    datos['nombre'] = nombre_prod
                    lista_agrupada[super_nombre].append(datos)
                    subtotales_super[super_nombre] += datos['total']
                
                lista_compra_visual = lista_agrupada
            except: pass

    return render(request, 'core/plan_semanal.html', {
        'calendario': calendario,
        'lista_compra': lista_compra_visual,
        'plan': plan,
        'subtotales': subtotales_super
    })