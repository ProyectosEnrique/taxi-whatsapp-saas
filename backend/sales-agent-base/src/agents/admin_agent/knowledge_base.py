"""
================================================================================
ESTRATEGIA 4: RAG - BASE DE CONOCIMIENTO PARA ADMIN AGENT
================================================================================
Sistema RAG (Retrieval Augmented Generation) simplificado para proporcionar
conocimiento contextual al asistente administrativo.

Incluye:
- Conocimiento de industria restaurantera
- Mejores practicas operativas
- Patrones estacionales y temporales
- Recomendaciones basadas en metricas

El sistema busca conocimiento relevante basado en la consulta del usuario
y lo inyecta en el prompt para mejorar las respuestas.
================================================================================
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ==============================================================================
# BASE DE CONOCIMIENTO - Industria Restaurantera
# ==============================================================================

RESTAURANT_KNOWLEDGE_BASE = {
    "food_cost": {
        "keywords": ["food cost", "costo de alimentos", "costo ingredientes", "costos", "insumos"],
        "knowledge": [
            {
                "topic": "Rangos saludables de Food Cost",
                "content": """
El Food Cost es el porcentaje de ingresos gastado en ingredientes.
- Excelente: < 28% (restaurantes premium, alta eficiencia)
- Bueno: 28-32% (operacion saludable)
- Aceptable: 32-35% (promedio industria)
- Alto: 35-40% (requiere atencion)
- Critico: > 40% (accion inmediata requerida)

Factores que afectan el food cost:
1. Mermas en cocina (desperdicio)
2. Porciones inconsistentes
3. Precios de proveedores
4. Robo o perdida de inventario
5. Menu engineering deficiente
""",
                "recommendations": [
                    "Implementar control de porciones con recetas estandarizadas",
                    "Negociar con proveedores trimestralmente",
                    "Hacer inventario semanal para detectar mermas",
                    "Analizar recetas de productos con alto costo"
                ]
            }
        ]
    },

    "margin": {
        "keywords": ["margen", "ganancia", "rentabilidad", "utilidad", "profit"],
        "knowledge": [
            {
                "topic": "Margenes de Utilidad en Restaurantes",
                "content": """
Margenes tipicos en la industria restaurantera:
- Margen Bruto: 60-70% (ventas - costo de alimentos)
- Margen Operativo: 10-15% (despues de gastos operativos)
- Margen Neto: 3-9% (utilidad final)

Desglose tipico de gastos:
- Food Cost: 28-35%
- Labor: 25-35%
- Renta: 5-10%
- Otros gastos: 15-25%
- Utilidad neta: 3-9%

Productos con mejor margen tipicamente:
1. Bebidas (especialmente alcoholicas): 70-85% margen
2. Postres: 60-75% margen
3. Entradas/Aperitivos: 65-75% margen
4. Platillos principales: 55-65% margen
""",
                "recommendations": [
                    "Promover bebidas y postres para mejorar margen",
                    "Crear combos que incluyan productos de alto margen",
                    "Revisar precios de platillos con margen < 50%"
                ]
            }
        ]
    },

    "peak_hours": {
        "keywords": ["hora pico", "horas pico", "rush", "ocupacion", "mas ventas", "mejor hora"],
        "knowledge": [
            {
                "topic": "Patrones de Horas Pico",
                "content": """
Horas pico tipicas en restaurantes mexicanos:
- Desayuno: 8:00-10:00 AM (si aplica)
- Comida: 1:00-3:00 PM (hora pico principal)
- Cena: 7:00-9:00 PM (segunda hora pico)

Factores que afectan la demanda:
- Dia de la semana (viernes/sabado mayor demanda)
- Quincenas (dias 15 y 30 mayor flujo)
- Clima (lluvia reduce visitas)
- Eventos locales
- Temporada (diciembre, dia de madres, etc.)

Estrategias para horas pico:
1. Personal completo 30 min antes del rush
2. Prep lista de platillos mas vendidos
3. Mesas listas y limpias
4. Sistema de reservaciones activo
""",
                "recommendations": [
                    "Aumentar personal en horas pico",
                    "Preparar mise en place antes del rush",
                    "Ofrecer promociones en horas valle"
                ]
            }
        ]
    },

    "promotions": {
        "keywords": ["promocion", "oferta", "descuento", "2x1", "especial", "promo"],
        "knowledge": [
            {
                "topic": "Estrategias de Promociones Efectivas",
                "content": """
Tipos de promociones y cuando usarlas:

1. DESCUENTO PORCENTUAL (10-20%):
   - Usar en: horas valle, dias lentos
   - No usar en: horas pico, productos estrella
   - Efecto: aumenta volumen, reduce margen

2. 2x1:
   - Usar en: productos de alto margen, bebidas
   - Ideal para: atraer grupos
   - Cuidado: calcular que el margen unitario cubra

3. COMBOS:
   - Mejor opcion para mejorar ticket promedio
   - Combinar producto estrella + alto margen
   - Percepcion de valor sin sacrificar margen

4. PROMOCION POR TIEMPO LIMITADO:
   - Crea urgencia
   - Ideal para probar nuevos productos
   - Funciona mejor con comunicacion en redes

5. HAPPY HOUR:
   - Solo bebidas (mayor margen)
   - Horarios: 4-7 PM tipicamente
   - Atrae clientes en horas muertas
""",
                "recommendations": [
                    "No hacer descuentos en productos estrella",
                    "Promociones deben tener fecha limite",
                    "Calcular impacto en margen antes de lanzar",
                    "Medir resultados de cada promocion"
                ]
            }
        ]
    },

    "products": {
        "keywords": ["producto", "menu", "platillo", "venta", "mas vendido", "estrella"],
        "knowledge": [
            {
                "topic": "Matriz BCG para Menu (Menu Engineering)",
                "content": """
Clasificacion de productos usando la Matriz BCG adaptada:

⭐ ESTRELLAS (Alto volumen + Alto margen):
- Son tus mejores productos
- Accion: Destacar en menu, promover activamente
- Ejemplo: Tu platillo signature con buen margen

🐄 VACAS DE EFECTIVO (Alto volumen + Bajo margen):
- Generan flujo pero poco profit
- Accion: Optimizar costos, ajustar precio si es posible
- Ejemplo: Platillos populares pero costosos de hacer

❓ INTERROGANTES (Bajo volumen + Alto margen):
- Potencial no aprovechado
- Accion: Invertir en promocion, capacitar meseros
- Ejemplo: Especialidades que pocos conocen

🐕 PERROS (Bajo volumen + Bajo margen):
- Ocupan espacio en menu sin retorno
- Accion: Eliminar o reformular drasticamente
- Ejemplo: Platillos que nadie pide y cuestan hacer

Analizar menu cada 3-6 meses con ventas reales.
""",
                "recommendations": [
                    "Destacar estrellas en menu fisico y digital",
                    "Capacitar meseros para sugerir productos estrella",
                    "Revisar recetas de vacas para reducir costos",
                    "Dar oportunidad a interrogantes con promociones"
                ]
            }
        ]
    },

    "seasonal": {
        "keywords": ["temporada", "estacional", "mes", "epoca", "navidad", "verano", "invierno"],
        "knowledge": [
            {
                "topic": "Patrones Estacionales en Restaurantes",
                "content": """
Calendario de alta y baja demanda en Mexico:

TEMPORADA ALTA:
- Diciembre: Posadas, Navidad, Año Nuevo (+30-50% ventas)
- Febrero: San Valentin (reservaciones importantes)
- Mayo: Dia de las Madres (pico del año para muchos)
- Septiembre: Fiestas patrias

TEMPORADA MEDIA:
- Enero: Post-fiestas, cuesta de enero
- Julio-Agosto: Vacaciones (variable segun ubicacion)
- Noviembre: Pre-navideño

TEMPORADA BAJA:
- Febrero (fuera de San Valentin)
- Marzo (post-quincenas)
- Octubre (despues de fiestas patrias)

Estrategias por temporada:
- Alta: Maximizar capacidad, precios premium
- Media: Promociones moderadas, fidelizacion
- Baja: Promociones agresivas, eventos especiales
""",
                "recommendations": [
                    "Planear inventario extra para temporada alta",
                    "Contratar personal temporal en diciembre",
                    "Crear promociones especiales para temporada baja",
                    "Reservar con anticipacion en dias especiales"
                ]
            }
        ]
    },

    "operations": {
        "keywords": ["operacion", "eficiencia", "personal", "staff", "servicio", "tiempo"],
        "knowledge": [
            {
                "topic": "Metricas Operativas Clave",
                "content": """
KPIs operativos que todo restaurante debe monitorear:

1. TIEMPO DE SERVICIO:
   - Objetivo comida: 12-18 minutos despues de ordenar
   - Objetivo bebidas: 3-5 minutos
   - Mesa libre a sentado: < 5 minutos

2. ROTACION DE MESAS:
   - Comida rapida: 3-4 rotaciones por servicio
   - Casual dining: 2-3 rotaciones
   - Fine dining: 1-2 rotaciones

3. TICKET PROMEDIO:
   - Monitorear diario
   - Comparar por mesero
   - Objetivo: aumentar 5-10% con upselling

4. PRODUCTIVIDAD LABORAL:
   - Ventas por hora de trabajo
   - Ideal: $150-250 por hora trabajada
   - Ajustar turnos segun demanda

5. DESPERDICIO:
   - Objetivo: < 2% de compras
   - Registrar mermas diariamente
   - Identificar productos problematicos
""",
                "recommendations": [
                    "Implementar sistema de tiempos en cocina",
                    "Capacitar meseros en tecnicas de upselling",
                    "Revisar horarios de personal semanalmente",
                    "Hacer inventario de mermas diario"
                ]
            }
        ]
    },

    "inventory": {
        "keywords": ["inventario", "stock", "agotado", "faltante", "proveedor", "compras"],
        "knowledge": [
            {
                "topic": "Gestion de Inventario",
                "content": """
Mejores practicas de inventario para restaurantes:

FRECUENCIA DE INVENTARIO:
- Productos perecederos: diario
- Carnes y mariscos: cada 2 dias
- Secos y enlatados: semanal
- Licores y bebidas: semanal

NIVELES DE REORDEN:
- Calcular consumo promedio diario
- Mantener 3-5 dias de stock de seguridad
- Considerar tiempo de entrega del proveedor

ROTACION FIFO (First In, First Out):
- Siempre usar producto mas antiguo primero
- Etiquetar con fecha de recepcion
- Revisar fechas de caducidad diariamente

PROVEEDORES:
- Tener 2-3 opciones por categoria
- Negociar precios trimestralmente
- Evaluar calidad consistentemente
""",
                "recommendations": [
                    "Implementar sistema FIFO estricto",
                    "Establecer niveles minimos de stock",
                    "Diversificar proveedores criticos",
                    "Hacer inventario sorpresa mensual"
                ]
            }
        ]
    },

    "customer_satisfaction": {
        "keywords": ["cliente", "satisfaccion", "queja", "servicio", "experiencia", "resena"],
        "knowledge": [
            {
                "topic": "Satisfaccion del Cliente",
                "content": """
Indicadores de satisfaccion del cliente:

METRICAS CLAVE:
- NPS (Net Promoter Score): Objetivo > 50
- Calificacion promedio: Objetivo > 4.2/5
- Tasa de retorno: Objetivo > 30%
- Quejas por 100 clientes: Objetivo < 2

PRINCIPALES MOTIVOS DE INSATISFACCION:
1. Tiempo de espera excesivo
2. Comida fria o de baja calidad
3. Errores en pedido
4. Mal servicio del personal
5. Limpieza deficiente

RECUPERACION DE SERVICIO:
- Responder quejas en < 24 horas
- Ofrecer solucion concreta
- Dar seguimiento posterior
- Convertir queja en oportunidad

El costo de perder un cliente es 5-7x mayor
que retener uno existente.
""",
                "recommendations": [
                    "Implementar encuesta de satisfaccion",
                    "Responder todas las resenas (positivas y negativas)",
                    "Capacitar personal en manejo de quejas",
                    "Programa de lealtad para clientes frecuentes"
                ]
            }
        ]
    },

    "upselling": {
        "keywords": ["upsell", "venta adicional", "sugerir", "aumentar ticket", "venta cruzada"],
        "knowledge": [
            {
                "topic": "Tecnicas de Upselling",
                "content": """
Estrategias efectivas de upselling en restaurantes:

1. BEBIDAS:
   - Sugerir al momento de sentar
   - Ofrecer refill antes de que termine
   - Promocionar bebidas especiales
   - Potencial: +15-20% en ticket

2. ENTRADAS:
   - Sugerir para compartir en grupos
   - Mencionar favoritos del chef
   - Potencial: +$80-150 por mesa

3. POSTRES:
   - Mostrar carrito o fotos atractivas
   - Ofrecer para compartir
   - Sugerir con cafe
   - Potencial: +$60-120 por mesa

4. UPGRADES:
   - Guarnicion premium
   - Proteina adicional
   - Tamano grande
   - Potencial: +$30-50 por persona

TECNICAS DE CONVERSACION:
- "Le recomiendo..." (no "¿quiere...?")
- Mencionar ingredientes atractivos
- Usar lenguaje descriptivo
- Sugerir maridaje especifico
""",
                "recommendations": [
                    "Capacitar meseros en tecnicas de sugerencia",
                    "Definir productos objetivo para upsell",
                    "Medir tasa de upsell por mesero",
                    "Incentivos para mejor desempeno en ventas"
                ]
            }
        ]
    },

    # ==========================================================================
    # IOT Y SEGURIDAD - Sensores y Alertas Criticas
    # ==========================================================================

    "iot_temperature": {
        "keywords": ["temperatura", "refrigerador", "congelador", "frio", "calor", "grados", "celsius", "termometro"],
        "knowledge": [
            {
                "topic": "Control de Temperatura y Cadena de Frio",
                "content": """
RANGOS CRITICOS DE TEMPERATURA EN RESTAURANTES:

🧊 REFRIGERACION (0-4°C):
- Carnes crudas: 0-2°C (maximo 4 dias)
- Lacteos: 2-4°C
- Verduras: 4-7°C
- Alimentos preparados: 0-4°C (maximo 3 dias)

❄️ CONGELACION (-18°C o menos):
- Carnes: -18°C (hasta 6 meses)
- Pescados: -20°C (hasta 3 meses)
- Helados: -18°C

🔥 ZONA DE PELIGRO (5-60°C):
- NUNCA mantener alimentos en este rango por mas de 2 horas
- Las bacterias se duplican cada 20 minutos

⚠️ CONSECUENCIAS DE NO ACTUAR:
1. SALUD PUBLICA:
   - Intoxicacion alimentaria (Salmonella, E.coli, Listeria)
   - Pueden causar hospitalizacion o muerte
   - Brotes afectan decenas de personas

2. LEGALES:
   - Clausura temporal o permanente por COFEPRIS
   - Multas de $50,000 a $500,000 MXN
   - Responsabilidad penal por lesiones

3. ECONOMICAS:
   - Perdida total de inventario (miles de pesos)
   - Demandas de clientes afectados
   - Destruccion de reputacion (resenas negativas virales)

4. OPERATIVAS:
   - Cierre de 3-7 dias minimo para inspeccion
   - Perdida de clientes permanente
   - Costo de reentrenamiento de personal
""",
                "recommendations": [
                    "URGENTE: Si temperatura > 7°C en refrigerador, revisar equipo inmediatamente",
                    "Registrar temperaturas cada 4 horas como minimo",
                    "Tener termometros de respaldo calibrados",
                    "Plan de contingencia para fallas de equipo",
                    "Capacitar personal en manejo seguro de alimentos"
                ]
            }
        ]
    },

    "iot_smoke_fire": {
        "keywords": ["humo", "fuego", "incendio", "detector", "alarma", "fumar", "quemado"],
        "knowledge": [
            {
                "topic": "Deteccion de Humo e Incendios",
                "content": """
🔥 SISTEMA DE DETECCION DE HUMO:

NIVELES DE ALERTA:
- Normal: < 20 ppm (operacion normal de cocina)
- Precaucion: 20-50 ppm (verificar cocina)
- Alerta: 50-100 ppm (INVESTIGAR INMEDIATAMENTE)
- Emergencia: > 100 ppm (EVACUAR)

⚠️ CONSECUENCIAS DE IGNORAR ALERTAS DE HUMO:

1. PERDIDA DE VIDAS:
   - Incendios en cocinas se propagan en 3-5 minutos
   - El humo mata antes que el fuego (asfixia)
   - Personal y clientes en riesgo mortal

2. DESTRUCCION TOTAL:
   - Un incendio puede destruir el restaurante en 15-20 minutos
   - Perdida de equipos: $500,000 - $2,000,000 MXN
   - Perdida de inventario, mobiliario, decoracion

3. LEGALES Y SEGUROS:
   - Si no hay protocolos, seguro puede no cubrir
   - Responsabilidad penal por negligencia
   - Demandas de empleados y clientes

4. CIERRE DEFINITIVO:
   - 60% de restaurantes no reabren despues de incendio
   - Costo de reconstruccion vs valor del negocio
   - Trauma psicologico del equipo

PROTOCOLO INMEDIATO:
1. Alerta > 50 ppm: Verificar TODA la cocina
2. Alerta > 100 ppm: Activar extintor si es fuego pequeno
3. Fuego no controlable: EVACUAR, llamar 911
4. NUNCA usar agua en fuego de aceite (usar extintor clase K)
""",
                "recommendations": [
                    "CRITICO: Verificar cocina inmediatamente si hay alerta",
                    "Tener extintores clase K en cocina (para aceites)",
                    "Simulacro de evacuacion cada 6 meses",
                    "Mantener salidas de emergencia despejadas SIEMPRE",
                    "Capacitar a TODO el personal en uso de extintores"
                ]
            }
        ]
    },

    "iot_gas": {
        "keywords": ["gas", "fuga", "lp", "natural", "propano", "olor", "explosion"],
        "knowledge": [
            {
                "topic": "Deteccion de Fugas de Gas",
                "content": """
⛽ MONITOREO DE GAS LP/NATURAL:

NIVELES DE CONCENTRACION:
- Normal: < 50 ppm
- Precaucion: 50-100 ppm (ventilacion necesaria)
- Peligro: 100-500 ppm (EVACUAR AREA)
- Critico: > 500 ppm (RIESGO DE EXPLOSION)

💥 CONSECUENCIAS DE IGNORAR FUGA DE GAS:

1. EXPLOSION:
   - Gas LP es mas pesado que el aire (se acumula abajo)
   - Una chispa puede causar explosion devastadora
   - Radio de destruccion de 10-50 metros
   - MUERTES MULTIPLES posibles

2. INTOXICACION:
   - Gas natural contiene monoxido de carbono
   - Sintomas: mareo, nausea, confusion
   - Exposicion prolongada: perdida de consciencia, muerte

3. LEGALES:
   - Negligencia criminal si hay victimas
   - Prision de 5-15 anos por homicidio culposo
   - Clausura permanente del establecimiento

4. ECONOMICAS:
   - Destruccion total del inmueble
   - Danos a propiedades vecinas (demandas millonarias)
   - Seguros no cubren si hay negligencia comprobada

PROTOCOLO DE EMERGENCIA:
1. NO encender luces ni equipos electricos
2. NO usar celulares dentro del area
3. Abrir ventanas y puertas inmediatamente
4. Cerrar valvula principal de gas
5. Evacuar y llamar a bomberos (911)
6. Esperar afuera hasta que lleguen autoridades
""",
                "recommendations": [
                    "EMERGENCIA: Si detecta gas > 100 ppm, EVACUAR SIN USAR ELECTRICIDAD",
                    "Revision de instalacion de gas cada 6 meses",
                    "Valvulas de cierre automatico en caso de fuga",
                    "Detector de gas con alarma sonora audible",
                    "Capacitar personal en protocolo de fuga de gas"
                ]
            }
        ]
    },

    "iot_humidity": {
        "keywords": ["humedad", "mojado", "seco", "condensacion", "moho", "hongos"],
        "knowledge": [
            {
                "topic": "Control de Humedad en Restaurantes",
                "content": """
💧 NIVELES OPTIMOS DE HUMEDAD:

AREAS DEL RESTAURANTE:
- Cocina: 40-60% (evitar condensacion)
- Almacen seco: 30-50% (proteger insumos)
- Comedor: 40-55% (confort del cliente)
- Refrigeradores: 85-95% (frescura de productos)

⚠️ PROBLEMAS POR HUMEDAD INADECUADA:

HUMEDAD ALTA (> 70%):
1. MOHO Y HONGOS:
   - Aparecen en 24-48 horas en condiciones humedas
   - Contaminan alimentos y superficies
   - Causan alergias y problemas respiratorios
   - Aspergillus puede ser mortal en inmunodeprimidos

2. DETERIORO DE ALIMENTOS:
   - Harinas y granos se apelmazan
   - Pan y tortillas se enmohecen rapido
   - Perdida de inventario significativa

3. INFRAESTRUCTURA:
   - Dano a paredes y techos
   - Oxidacion de equipos metalicos
   - Pisos resbaladizos (riesgo de caidas)

HUMEDAD BAJA (< 30%):
- Resequedad de alimentos
- Incomodidad de clientes y personal
- Mayor polvo en el aire
""",
                "recommendations": [
                    "Mantener humedad entre 40-60% en areas de servicio",
                    "Revisar sistema de ventilacion si humedad > 70%",
                    "Inspeccionar almacenes por moho mensualmente",
                    "Usar deshumidificadores en epocas de lluvia"
                ]
            }
        ]
    },

    "iot_co2": {
        "keywords": ["co2", "dioxido", "carbono", "aire", "ventilacion", "oxigeno", "respirar"],
        "knowledge": [
            {
                "topic": "Calidad del Aire y CO2",
                "content": """
🌫️ NIVELES DE CO2 EN ESPACIOS CERRADOS:

CONCENTRACIONES Y EFECTOS:
- Exterior normal: 400 ppm
- Interior aceptable: 400-800 ppm
- Necesita ventilacion: 800-1000 ppm
- Inaceptable: 1000-2000 ppm
- Peligroso: > 2000 ppm

⚠️ CONSECUENCIAS DE CO2 ELEVADO:

1. SALUD INMEDIATA:
   - 1000+ ppm: Fatiga, dolor de cabeza, dificultad para concentrarse
   - 2000+ ppm: Somnolencia severa, nauseas
   - 5000+ ppm: Mareo intenso, posible perdida de consciencia
   - 40000+ ppm: Potencialmente mortal

2. CLIENTES Y PERSONAL:
   - Ambiente incomodo (sensacion de "aire viciado")
   - Quejas frecuentes
   - Menor tiempo de estancia de clientes
   - Baja productividad del personal

3. RIESGO COVID Y ENFERMEDADES:
   - CO2 alto = mala ventilacion = mayor riesgo de contagio
   - Aerosoles permanecen en el aire
   - Responsabilidad del establecimiento

4. REGULATORIO:
   - STPS establece limites de exposicion laboral
   - Multas por condiciones insalubres de trabajo
""",
                "recommendations": [
                    "Si CO2 > 1000 ppm, abrir ventanas o aumentar ventilacion",
                    "Instalar sistema de ventilacion con renovacion de aire",
                    "Monitorear CO2 especialmente en horas pico",
                    "Plantas pueden ayudar pero no reemplazan ventilacion"
                ]
            }
        ]
    },

    "iot_motion_security": {
        "keywords": ["movimiento", "intruso", "seguridad", "robo", "alarma", "vigilancia", "camara"],
        "knowledge": [
            {
                "topic": "Seguridad y Deteccion de Movimiento",
                "content": """
👁️ SISTEMA DE DETECCION DE MOVIMIENTO:

ZONAS CRITICAS A MONITOREAR:
- Almacen de insumos
- Caja registradora / oficina
- Entradas traseras
- Area de licores (alto valor)
- Refrigeradores (robo de carnes)

⚠️ CONSECUENCIAS DE IGNORAR ALERTAS:

1. ROBO INTERNO:
   - 75% de robos en restaurantes son de empleados
   - Promedio de perdida: $50,000-$200,000 MXN/ano
   - Merma "inexplicable" de inventario

2. ROBO EXTERNO:
   - Intrusos despues del cierre
   - Robo de equipos y efectivo
   - Vandalismo

3. SEGURIDAD DEL PERSONAL:
   - Asaltos a empleados que cierran
   - Riesgo de violencia
   - Responsabilidad patronal

PROTOCOLO DE ALERTA NOCTURNA:
1. Movimiento detectado fuera de horario = ALERTA INMEDIATA
2. Verificar camaras en vivo (si hay)
3. NO entrar solo a investigar
4. Llamar a seguridad o policia
5. Documentar para seguro
""",
                "recommendations": [
                    "Movimiento fuera de horario: verificar camaras antes de entrar",
                    "Sistema de camaras con respaldo en la nube",
                    "Protocolo de cierre con 2 personas minimo",
                    "Inventario diario de productos de alto valor"
                ]
            }
        ]
    },

    "iot_general": {
        "keywords": ["sensor", "iot", "nodo", "esp32", "monitoreo", "alerta", "estado"],
        "knowledge": [
            {
                "topic": "Sistema IoT de Monitoreo General",
                "content": """
📡 SISTEMA DE SENSORES IoT DEL RESTAURANTE:

TIPOS DE SENSORES INSTALADOS:
- 🌡️ Temperatura: Refrigeradores, congeladores, cocina
- 💧 Humedad: Almacenes, areas de servicio
- 🔥 Humo: Cocina, comedor, almacenes
- ⛽ Gas: Cocina, area de tanques
- 🌫️ CO2: Comedor, areas cerradas
- 👁️ Movimiento: Seguridad nocturna

BENEFICIOS DEL MONITOREO 24/7:
1. Prevencion de perdidas economicas
2. Cumplimiento de normativas sanitarias
3. Seguridad de personal y clientes
4. Evidencia para seguros
5. Tranquilidad operativa

⚠️ IMPORTANCIA DE ATENDER ALERTAS:

Las alertas NO son molestias, son PROTECCION:
- Cada alerta ignorada es un riesgo que se acepta
- El costo de atender una alerta: minutos
- El costo de ignorarla: potencialmente catastrofico

JERARQUIA DE ALERTAS:
🔴 CRITICA (Humo, Gas > 100ppm): Accion en SEGUNDOS
🟠 ALTA (Temperatura fuera de rango): Accion en MINUTOS
🟡 MEDIA (Humedad alta, CO2 elevado): Accion en HORAS
🟢 INFORMATIVA (Estado de equipos): Revision programada
""",
                "recommendations": [
                    "Revisar dashboard de sensores al inicio de cada turno",
                    "Configurar notificaciones en celular para alertas criticas",
                    "Hacer prueba de sensores semanalmente",
                    "Mantener registro de alertas y acciones tomadas"
                ]
            }
        ]
    }
}


# ==============================================================================
# RETRIEVER - Buscador de Conocimiento Relevante
# ==============================================================================

@dataclass
class KnowledgeResult:
    """Resultado de busqueda en base de conocimiento"""
    topic: str
    content: str
    recommendations: List[str]
    relevance_score: float
    category: str


class KnowledgeRetriever:
    """
    Recuperador de conocimiento relevante para consultas del admin.

    Usa matching de keywords y similitud basica para encontrar
    conocimiento relevante a la consulta del usuario.
    """

    def __init__(self, knowledge_base: Dict = None):
        """
        Inicializar retriever.

        Args:
            knowledge_base: Base de conocimiento (default: RESTAURANT_KNOWLEDGE_BASE)
        """
        self.knowledge_base = knowledge_base or RESTAURANT_KNOWLEDGE_BASE
        logger.info(f"[KnowledgeRetriever] Inicializado con {len(self.knowledge_base)} categorias")

    def retrieve(
        self,
        query: str,
        top_k: int = 2,
        min_relevance: float = 0.3
    ) -> List[KnowledgeResult]:
        """
        Recuperar conocimiento relevante para una consulta.

        Args:
            query: Consulta del usuario
            top_k: Numero maximo de resultados
            min_relevance: Score minimo de relevancia

        Returns:
            Lista de KnowledgeResult ordenados por relevancia
        """
        query_lower = query.lower()
        results = []

        for category, data in self.knowledge_base.items():
            keywords = data.get("keywords", [])
            knowledge_items = data.get("knowledge", [])

            # Calcular relevancia basada en keywords
            relevance = self._calculate_relevance(query_lower, keywords)

            if relevance >= min_relevance:
                for item in knowledge_items:
                    results.append(KnowledgeResult(
                        topic=item.get("topic", category),
                        content=item.get("content", ""),
                        recommendations=item.get("recommendations", []),
                        relevance_score=relevance,
                        category=category
                    ))

        # Ordenar por relevancia y limitar
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]

    def _calculate_relevance(self, query: str, keywords: List[str]) -> float:
        """
        Calcular score de relevancia basado en keywords.

        Args:
            query: Consulta en minusculas
            keywords: Lista de keywords de la categoria

        Returns:
            Score de 0.0 a 1.0
        """
        if not keywords:
            return 0.0

        matches = 0
        partial_matches = 0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in query:
                matches += 1
            elif any(word in query for word in keyword_lower.split()):
                partial_matches += 0.5

        total_score = (matches + partial_matches) / len(keywords)
        return min(1.0, total_score)

    def get_context_for_query(self, query: str) -> str:
        """
        Obtener contexto formateado para inyectar en el prompt.

        Args:
            query: Consulta del usuario

        Returns:
            Texto con conocimiento relevante formateado
        """
        results = self.retrieve(query, top_k=2)

        if not results:
            return ""

        context_parts = []
        for result in results:
            context_parts.append(f"""
### {result.topic}
{result.content.strip()}

**Recomendaciones:**
{chr(10).join(f'- {r}' for r in result.recommendations[:3])}
""")

        return "\n".join(context_parts)

    def get_recommendations_for_topic(self, topic: str) -> List[str]:
        """
        Obtener recomendaciones especificas para un tema.

        Args:
            topic: Tema/categoria a buscar

        Returns:
            Lista de recomendaciones
        """
        topic_lower = topic.lower()

        for category, data in self.knowledge_base.items():
            if category == topic_lower:
                recommendations = []
                for item in data.get("knowledge", []):
                    recommendations.extend(item.get("recommendations", []))
                return recommendations

            # Buscar en keywords
            if any(topic_lower in kw.lower() for kw in data.get("keywords", [])):
                recommendations = []
                for item in data.get("knowledge", []):
                    recommendations.extend(item.get("recommendations", []))
                return recommendations

        return []


# ==============================================================================
# SINGLETON Y HELPERS
# ==============================================================================

_knowledge_retriever: Optional[KnowledgeRetriever] = None


def get_knowledge_retriever() -> KnowledgeRetriever:
    """Obtener instancia singleton del retriever"""
    global _knowledge_retriever
    if _knowledge_retriever is None:
        _knowledge_retriever = KnowledgeRetriever()
    return _knowledge_retriever


def get_relevant_knowledge(query: str) -> str:
    """
    Helper para obtener conocimiento relevante.

    Args:
        query: Consulta del usuario

    Returns:
        Texto con conocimiento contextual
    """
    retriever = get_knowledge_retriever()
    return retriever.get_context_for_query(query)


def get_topic_recommendations(topic: str) -> List[str]:
    """
    Helper para obtener recomendaciones de un tema.

    Args:
        topic: Tema a buscar

    Returns:
        Lista de recomendaciones
    """
    retriever = get_knowledge_retriever()
    return retriever.get_recommendations_for_topic(topic)
