import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Min, Q
from .models import Receta, PerfilUsuario, PlanSemanal, Supermercado

# REDIRECCIÓN RAÍZ
def home(request):
    if request.user.is_authenticated:
        return redirect('plan_semanal')
    else:
        return redirect('login')

# 1. VISTA: LISTA DE RECETAS (Con Precio Dinámico)
def lista_recetas(request):
    recetas = Receta.objects.all()
    perfil = None
    metas = None
    limite_coste = 0

    if request.user.is_authenticated:
        try:
            perfil = PerfilUsuario.objects.get(usuario=request.user)
            mis_supers = perfil.supermercados_seleccionados.all()

            # --- LÓGICA DE PRECIOS V2 ---
            # Si el usuario tiene supermercados, calculamos el precio mínimo en ELLOS.
            if mis_supers.exists():
                recetas = recetas.annotate(
                    precio_usuario=Min(
                        'costes_por_supermercado__coste',
                        filter=Q(costes_por_supermercado__supermercado__in=mis_supers)
                    )
                )
            else:
                # Si no tiene súper seleccionado, mostramos el mínimo global
                recetas = recetas.annotate(
                    precio_usuario=Min('costes_por_supermercado__coste')
                )

            # --- MACROS ---
            metas = {
                'calorias': perfil.gasto_energetico_diario,
                'proteinas': perfil.objetivo_proteinas,
                'grasas': perfil.objetivo_grasas,
                'hidratos': perfil.objetivo_hidratos,
            }

            # Filtros de Electrodomésticos
            if not perfil.tiene_horno: recetas = recetas.exclude(es_apta_horno=True)
            if not perfil.tiene_airfryer: recetas = recetas.exclude(es_apta_airfryer=True)
            if not perfil.tiene_microondas: recetas = recetas.exclude(es_apta_microondas=True)

            if perfil.presupuesto_semanal > 0:
                limite_coste = perfil.presupuesto_semanal / 14

        except PerfilUsuario.DoesNotExist:
            pass
    else:
        # Usuario anónimo: Precio mínimo global
        recetas = recetas.annotate(precio_usuario=Min('costes_por_supermercado__coste'))

    # Filtros Manuales (Buscador)
    query = request.GET.get('q')
    if query: recetas = recetas.filter(titulo__icontains=query)
    if request.GET.get('sarten'): recetas = recetas.filter(es_apta_sarten=True)
    if request.GET.get('airfryer'): recetas = recetas.filter(es_apta_airfryer=True)
    if request.GET.get('horno'): recetas = recetas.filter(es_apta_horno=True)

    return render(request, 'core/lista_recetas.html', {
        'recetas': recetas, 
        'perfil': perfil, 
        'metas': metas, 
        'limite_coste': limite_coste
    })

# 2. VISTA: DETALLE DE RECETA
def detalle_receta(request, receta_id):
    receta = get_object_or_404(Receta, id=receta_id)
    
    # Obtener desglose de precios por súper para mostrar comparativa
    # Solo mostramos los que son "posibles" (tienen todos los ingredientes)
    costes = receta.costes_por_supermercado.filter(es_posible=True).select_related('supermercado').order_by('coste')
    
    # NOTA: Asegúrate de que el template se llame 'detalles_receta.html' o ajusta aquí el nombre
    return render(request, 'core/detalles_receta.html', {
        'receta': receta,
        'costes': costes
    })

# 3. VISTA: REGISTRO
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

# 4. VISTA: PERFIL
@login_required
def perfil(request):
    perfil_usuario, created = PerfilUsuario.objects.get_or_create(usuario=request.user)
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
        
        # Guardar Supermercados
        supers_ids = request.POST.getlist('supermercados')
        perfil_usuario.supermercados_seleccionados.set(supers_ids)
        
        perfil_usuario.save()
        return redirect('plan_semanal')

    return render(request, 'core/perfil.html', {
        'perfil': perfil_usuario,
        'supermercados': todos_supers
    })

# 5. VISTA: VER PLAN SEMANAL
@login_required
def ver_plan_semanal(request):
    plan = PlanSemanal.objects.filter(usuario=request.user).order_by('-fecha_inicio').first()
    
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    calendario = {i: {'nombre': dias_semana[i], 'comida': None, 'cena': None} for i in range(7)}
    lista_compra_visual = {} 

    if plan:
        comidas = plan.comidas.all().select_related('receta')
        for comida in comidas:
            if comida.momento == 'COMIDA':
                calendario[comida.dia_semana]['comida'] = comida.receta
            elif comida.momento == 'CENA':
                calendario[comida.dia_semana]['cena'] = comida.receta
        
        # Procesar JSON de compra para la vista agrupada
        if plan.lista_compra_generada:
            try:
                raw_lista = json.loads(plan.lista_compra_generada)
                # Agrupar por supermercado: { 'Mercadona': [item1, item2], 'Lidl': [...] }
                lista_agrupada = {}
                for nombre_prod, datos in raw_lista.items():
                    super_nombre = datos.get('super', 'Otros')
                    if super_nombre not in lista_agrupada:
                        lista_agrupada[super_nombre] = []
                    
                    datos['nombre'] = nombre_prod
                    lista_agrupada[super_nombre].append(datos)
                
                lista_compra_visual = lista_agrupada

            except json.JSONDecodeError:
                lista_compra_visual = {}

    return render(request, 'core/plan_semanal.html', {
        'calendario': calendario,
        'lista_compra': lista_compra_visual,
        'plan': plan
    })