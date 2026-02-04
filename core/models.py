from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Min

# --- 1. MODELO SUPERMERCADO (Ahora es fundamental) ---
class Supermercado(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    color_brand = models.CharField(max_length=7, default="#000000", help_text="Color hexadecimal para la UI")
    
    def __str__(self):
        return self.nombre

# --- 2. MODELO PERFIL DE USUARIO ---
class PerfilUsuario(models.Model):
    OBJETIVOS = [
        ('PERDER', 'Perder Peso'),
        ('GANAR', 'Ganar Músculo'),
        ('MANTENER', 'Mantener Peso'),
    ]
    ACTIVIDAD = [
        ('SEDENTARIO', 'Sedentario (Oficina, poco ejercicio)'),
        ('LIGERO', 'Ligero (1-3 días/sem)'),
        ('MODERADO', 'Moderado (3-5 días/sem)'),
        ('ALTO', 'Alto (6-7 días/sem)'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    
    # Fisiología
    edad = models.IntegerField(default=30)
    peso_kg = models.FloatField(default=70.0)
    altura_cm = models.IntegerField(default=170)
    genero = models.CharField(max_length=10, choices=[('M', 'Masculino'), ('F', 'Femenino')], default='M')
    objetivo = models.CharField(max_length=10, choices=OBJETIVOS, default='MANTENER')
    nivel_actividad = models.CharField(max_length=10, choices=ACTIVIDAD, default='SEDENTARIO')

    # Metas Nutricionales (Calculadas)
    gasto_energetico_diario = models.IntegerField(default=2000)
    objetivo_proteinas = models.IntegerField(default=0)
    objetivo_grasas = models.IntegerField(default=0)
    objetivo_hidratos = models.IntegerField(default=0)

    # LOGÍSTICA DE MERCADO (EL NUEVO CEREBRO)
    supermercados_seleccionados = models.ManyToManyField(Supermercado, blank=True, related_name='usuarios')
    presupuesto_semanal = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    
    # Electrodomésticos y Tiempos
    tiene_horno = models.BooleanField(default=True)
    tiene_microondas = models.BooleanField(default=True)
    tiene_airfryer = models.BooleanField(default=False)
    tiempo_cocina_diario = models.IntegerField(default=30)

    def calcular_macronutrientes(self):
        # 1. TMB (Harris-Benedict Revisada)
        if self.genero == 'M':
            tmb = 10 * self.peso_kg + 6.25 * self.altura_cm - 5 * self.edad + 5
        else:
            tmb = 10 * self.peso_kg + 6.25 * self.altura_cm - 5 * self.edad - 161
            
        # 2. TDEE
        factores = {'SEDENTARIO': 1.2, 'LIGERO': 1.375, 'MODERADO': 1.55, 'ALTO': 1.725}
        tdee = tmb * factores.get(self.nivel_actividad, 1.2)
        
        # 3. Ajuste Objetivo
        factor_prot, factor_gras = 1.5, 1.0
        if self.objetivo == 'PERDER': 
            tdee -= 400; factor_prot = 2.0; factor_gras = 0.8
        elif self.objetivo == 'GANAR': 
            tdee += 300; factor_prot = 1.8; factor_gras = 1.0
        
        # 4. Gramos
        prot = int(self.peso_kg * factor_prot)
        gras = int(self.peso_kg * factor_gras)
        cals_rest = max(200, tdee - ((prot * 4) + (gras * 9)))
        hidr = int(cals_rest / 4)

        return int(tdee), prot, gras, hidr

    def save(self, *args, **kwargs):
        tdee, prot, gras, hidr = self.calcular_macronutrientes()
        self.gasto_energetico_diario = tdee
        self.objetivo_proteinas = prot
        self.objetivo_grasas = gras
        self.objetivo_hidratos = hidr
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

# --- 3. MODELO INGREDIENTE BASE (Agnóstico del Supermercado) ---
class IngredienteBase(models.Model):
    CATEGORIAS = [
        ('Fruta', 'Fruta'), ('Verdura', 'Verdura'), ('Carniceria', 'Carnicería'),
        ('Pescaderia', 'Pescadería'), ('Lacteos', 'Lácteos'), ('Despensa', 'Despensa'),
        ('Huevos', 'Huevos'), ('Otros', 'Otros')
    ]
    nombre = models.CharField(max_length=100, unique=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='Otros')
    # Macros promedio (Referencia)
    calorias = models.IntegerField(default=0)
    proteinas = models.FloatField(default=0.0)
    grasas = models.FloatField(default=0.0)
    hidratos = models.FloatField(default=0.0)
    dias_caducidad = models.IntegerField(default=7)

    def __str__(self):
        return self.nombre

# --- 4. MODELO PRODUCTO REAL (Vinculado a un Supermercado) ---
class ProductoReal(models.Model):
    ingrediente_base = models.ForeignKey(IngredienteBase, on_delete=models.CASCADE, related_name='productos_disponibles')
    supermercado = models.ForeignKey(Supermercado, on_delete=models.CASCADE)
    
    nombre_comercial = models.CharField(max_length=200)
    precio_actual = models.DecimalField(max_digits=6, decimal_places=2)
    
    # Normalización para algoritmos
    peso_gramos = models.IntegerField(default=1000, help_text="Peso neto normalizado")
    precio_por_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Datos crudos del scraper (para auditoría)
    tipo_unidad_original = models.CharField(max_length=10, default='KG')
    precio_referencia_original = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    
    imagen_url = models.URLField(max_length=500, blank=True, null=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Autocalcular precio por KG real para comparativas justas
        if self.peso_gramos > 0 and self.precio_actual > 0:
            self.precio_por_kg = (self.precio_actual / Decimal(self.peso_gramos)) * 1000
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_comercial} ({self.supermercado.nombre}) - {self.precio_actual}€"

# --- 5. MODELO RECETAS (Estructural) ---
class Receta(models.Model):
    titulo = models.CharField(max_length=200)
    tiempo_preparacion = models.IntegerField()
    # Tags técnicos
    es_apta_sarten = models.BooleanField(default=False)
    es_apta_airfryer = models.BooleanField(default=False)
    es_apta_horno = models.BooleanField(default=False)
    es_apta_microondas = models.BooleanField(default=False)
    es_apta_tupper = models.BooleanField(default=True)
    
    # Macros (Estos sí son intrínsecos de la receta, aprox)
    calorias = models.IntegerField(default=0)
    proteinas = models.FloatField(default=0.0)
    grasas = models.FloatField(default=0.0)
    hidratos = models.FloatField(default=0.0)

    # NOTA: ELIMINADO precio_estimado. Ahora se consulta en CostePorSupermercado.

    def obtener_precio_para_usuario(self, perfil_usuario):
        """
        Retorna el coste mínimo posible usando SOLO los supermercados del usuario.
        Si no tiene supermercados, retorna None.
        """
        mis_supers = perfil_usuario.supermercados_seleccionados.all()
        if not mis_supers.exists():
            return None
        
        # Buscamos el coste pre-calculado más barato entre sus opciones
        costes = self.costes_por_supermercado.filter(supermercado__in=mis_supers)
        if costes.exists():
            return costes.aggregate(Min('coste'))['coste__min']
        return None

    def recalcular_macros(self):
        c, p, g, h = 0, 0, 0, 0
        for item in self.ingredientes.all():
            gramos = item.cantidad_gramos
            base = item.ingrediente_base
            c += (base.calorias / 100) * gramos
            p += (base.proteinas / 100) * gramos
            g += (base.grasas / 100) * gramos
            h += (base.hidratos / 100) * gramos
        self.calorias = int(c)
        self.proteinas = round(p, 1)
        self.grasas = round(g, 1)
        self.hidratos = round(h, 1)
        self.save()

    def __str__(self):
        return self.titulo

# --- 6. MODELO COSTE DINÁMICO (Nuevo Cerebro Económico) ---
class CostePorSupermercado(models.Model):
    """
    Guarda cuánto cuesta hacer la Receta X comprando TODO en el Supermercado Y.
    Esto permite filtrar rápidamente: "Recetas baratas en Mercadona".
    """
    receta = models.ForeignKey(Receta, related_name='costes_por_supermercado', on_delete=models.CASCADE)
    supermercado = models.ForeignKey(Supermercado, on_delete=models.CASCADE)
    coste = models.DecimalField(max_digits=6, decimal_places=2)
    es_posible = models.BooleanField(default=True, help_text="False si el súper no tiene todos los ingredientes")
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('receta', 'supermercado')

# --- 7. INGREDIENTES DE RECETA ---
class RecetaIngrediente(models.Model):
    receta = models.ForeignKey(Receta, related_name='ingredientes', on_delete=models.CASCADE)
    ingrediente_base = models.ForeignKey(IngredienteBase, on_delete=models.CASCADE)
    cantidad_gramos = models.IntegerField()

    def __str__(self):
        return f"{self.ingrediente_base.nombre} ({self.cantidad_gramos}g)"

# --- 8. PLAN SEMANAL ---
class PlanSemanal(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)
    # Guardamos el JSON de la compra para congelar el precio en el momento de la generación
    lista_compra_snapshot = models.TextField(blank=True, null=True) 
    coste_total_estimado = models.DecimalField(max_digits=8, decimal_places=2, default=0)

class ComidaPlanificada(models.Model):
    plan = models.ForeignKey(PlanSemanal, related_name='comidas', on_delete=models.CASCADE)
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE)
    dia_semana = models.IntegerField(choices=[(i, str(i)) for i in range(7)])
    momento = models.CharField(max_length=10, choices=[('COMIDA','Comida'), ('CENA','Cena')])