from django.contrib import admin
from .models import (
    IngredienteBase, 
    ProductoReal, 
    Receta, 
    RecetaIngrediente, 
    PlanSemanal, 
    ComidaPlanificada,
    Supermercado,
    PerfilUsuario,
    CostePorSupermercado  # <--- NUEVO MODELO IMPORTADO
)

# 1. Configuración de INGREDIENTE BASE
@admin.register(IngredienteBase)
class IngredienteBaseAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'calorias', 'dias_caducidad')
    list_filter = ('categoria',)
    search_fields = ('nombre',)

# 2. Configuración de PRODUCTO REAL
@admin.register(ProductoReal)
class ProductoRealAdmin(admin.ModelAdmin):
    # Actualizado a los nuevos campos de la V2
    list_display = (
        'nombre_comercial', 
        'supermercado',
        'precio_actual', 
        'peso_gramos',
        'precio_por_kg',     # Campo nuevo calculado
        'ultima_actualizacion'
    )
    list_filter = ('supermercado', 'ingrediente_base__categoria')
    search_fields = ('nombre_comercial', 'ingrediente_base__nombre')

# 3. Configuración de RECETAS
class RecetaIngredienteInline(admin.TabularInline):
    model = RecetaIngrediente
    extra = 1
    autocomplete_fields = ['ingrediente_base']

# Nuevo Inline para ver los precios por súper dentro de la receta
class CostePorSupermercadoInline(admin.TabularInline):
    model = CostePorSupermercado
    extra = 0
    readonly_fields = ('coste', 'ultima_actualizacion')
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    # Eliminado 'precio_estimado' que ya no existe en el modelo
    list_display = ('titulo', 'tiempo_preparacion', 'calorias', 'proteinas', 'grasas', 'hidratos')
    
    list_filter = ('es_apta_airfryer', 'es_apta_sarten', 'es_apta_horno') 
    search_fields = ('titulo',)
    # Añadimos ambos inlines: ingredientes y costes
    inlines = [RecetaIngredienteInline, CostePorSupermercadoInline]

# 4. Configuración del PLAN SEMANAL
class ComidaPlanificadaInline(admin.TabularInline):
    model = ComidaPlanificada
    extra = 0
    readonly_fields = ('dia_semana', 'momento', 'receta')
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

@admin.register(PlanSemanal)
class PlanSemanalAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_inicio', 'coste_total_estimado') 
    inlines = [ComidaPlanificadaInline]

# 5. Otros registros simples
admin.site.register(Supermercado)
admin.site.register(PerfilUsuario)
# Registramos CostePorSupermercado también por separado por si queremos auditar
@admin.register(CostePorSupermercado)
class CostePorSupermercadoAdmin(admin.ModelAdmin):
    list_display = ('receta', 'supermercado', 'coste', 'es_posible')
    list_filter = ('supermercado', 'es_posible')