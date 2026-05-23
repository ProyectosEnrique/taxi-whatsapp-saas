"""
================================================================================
ADMIN TOOLS - Function Calling para Admin Agent
================================================================================
Herramientas/funciones que el Admin Agent puede ejecutar.
Cada herramienta corresponde a una accion administrativa.
================================================================================
"""

import logging
import os
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


# ==============================================================================
# TOOL DEFINITIONS (para LLM function calling)
# ==============================================================================

ADMIN_TOOL_DEFINITIONS = [
    {
        "name": "get_sales_report",
        "description": "Obtener reporte de ventas por periodo. Usa esto cuando el admin pregunte por ventas, ingresos, o cuanto se vendio.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "yesterday", "week", "month"],
                    "description": "Periodo del reporte: hoy, ayer, semana o mes"
                },
                "category": {
                    "type": "string",
                    "description": "Filtrar por categoria (opcional)"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "get_top_products",
        "description": "Obtener productos mas vendidos. Usa esto cuando pregunten por los mas vendidos o populares.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Cantidad de productos a mostrar (default: 5)"
                },
                "period": {
                    "type": "string",
                    "enum": ["today", "week", "month"],
                    "description": "Periodo de analisis"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_orders_count",
        "description": "Obtener cantidad de ordenes. Usa esto cuando pregunten cuantas ordenes hay o hubo.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "yesterday", "week", "month"],
                    "description": "Periodo a consultar"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "completed", "cancelled", "all"],
                    "description": "Estado de las ordenes"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "create_promotion",
        "description": "Crear una nueva promocion. Usa esto cuando el admin quiera crear ofertas, descuentos, 2x1, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre de la promocion"
                },
                "promotion_type": {
                    "type": "string",
                    "enum": ["percentage", "fixed", "2x1", "combo"],
                    "description": "Tipo: porcentaje, descuento fijo, 2x1, o combo"
                },
                "discount_value": {
                    "type": "number",
                    "description": "Valor del descuento (porcentaje o cantidad)"
                },
                "products": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de productos aplicables (nombres)"
                },
                "start_time": {
                    "type": "string",
                    "description": "Hora de inicio (HH:MM)"
                },
                "end_time": {
                    "type": "string",
                    "description": "Hora de fin (HH:MM)"
                },
                "days": {
                    "type": "string",
                    "description": "Dias de la semana (lunes,martes,...)"
                }
            },
            "required": ["name", "promotion_type"]
        }
    },
    {
        "name": "toggle_promotion",
        "description": "Activar o desactivar una promocion existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "promotion_name": {
                    "type": "string",
                    "description": "Nombre de la promocion"
                },
                "active": {
                    "type": "boolean",
                    "description": "True para activar, False para desactivar"
                }
            },
            "required": ["promotion_name", "active"]
        }
    },
    {
        "name": "list_promotions",
        "description": "Listar promociones activas o todas. Usa esto cuando pregunten que promociones hay.",
        "parameters": {
            "type": "object",
            "properties": {
                "active_only": {
                    "type": "boolean",
                    "description": "Solo mostrar promociones activas"
                }
            },
            "required": []
        }
    },
    {
        "name": "create_product",
        "description": "Crear un nuevo platillo/producto en el menu. Usa esto cuando el admin quiera agregar un nuevo platillo, bebida o producto al menu.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre del platillo o producto"
                },
                "price": {
                    "type": "number",
                    "description": "Precio en pesos mexicanos"
                },
                "description": {
                    "type": "string",
                    "description": "Descripcion del platillo (opcional)"
                },
                "category": {
                    "type": "string",
                    "description": "Nombre de la categoria (ej: hamburguesas, bebidas, postres)"
                },
                "ingredients": {
                    "type": "string",
                    "description": "Ingredientes principales separados por coma (opcional)"
                },
                "spice_level": {
                    "type": "integer",
                    "description": "Nivel de picante: 0=nada, 1=bajo, 2=medio, 3=alto (default: 0)"
                },
                "preparation_time": {
                    "type": "integer",
                    "description": "Tiempo de preparacion en minutos (default: 15)"
                },
                "cost": {
                    "type": "number",
                    "description": "Costo de preparacion (opcional, para calcular margen)"
                }
            },
            "required": ["name", "price"]
        }
    },
    {
        "name": "toggle_product",
        "description": "Activar o desactivar un producto del menu. Usa esto para marcar agotados o disponibles.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Nombre del producto"
                },
                "available": {
                    "type": "boolean",
                    "description": "True para disponible, False para agotado"
                }
            },
            "required": ["product_name", "available"]
        }
    },
    {
        "name": "update_product_price",
        "description": "Actualizar el precio de un producto.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Nombre del producto"
                },
                "new_price": {
                    "type": "number",
                    "description": "Nuevo precio en pesos"
                }
            },
            "required": ["product_name", "new_price"]
        }
    },
    {
        "name": "get_unavailable_products",
        "description": "Obtener lista de productos agotados/no disponibles.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_hourly_sales",
        "description": "Obtener ventas por hora del dia. Util para identificar horas pico.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Fecha en formato YYYY-MM-DD (default: hoy)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_average_ticket",
        "description": "Obtener ticket promedio por periodo.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "week", "month"],
                    "description": "Periodo de analisis"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "generate_daily_report",
        "description": "Generar reporte completo del dia con todas las metricas.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Fecha del reporte (YYYY-MM-DD). Default: hoy"
                }
            },
            "required": []
        }
    },

    # =========================================================================
    # ESTRATEGIA 3: HERRAMIENTAS DE ANALISIS FINANCIERO/OPERATIVO
    # =========================================================================
    {
        "name": "analyze_food_cost",
        "description": "Analizar food cost y rentabilidad. Usa esto cuando pregunten por costos, rentabilidad, o food cost.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "week", "month"],
                    "description": "Periodo de analisis"
                },
                "include_recommendations": {
                    "type": "boolean",
                    "description": "Incluir recomendaciones de mejora"
                }
            },
            "required": []
        }
    },
    {
        "name": "analyze_product_performance",
        "description": "Analizar rendimiento de productos usando matriz BCG (estrellas, vacas, perros, interrogantes). Usa esto para identificar que productos promocionar o retirar.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["week", "month"],
                    "description": "Periodo de analisis"
                },
                "category": {
                    "type": "string",
                    "description": "Filtrar por categoria (opcional)"
                }
            },
            "required": []
        }
    },
    {
        "name": "analyze_sales_trend",
        "description": "Analizar tendencia de ventas y predecir comportamiento. Usa esto cuando pregunten por tendencias, proyecciones o comparativas.",
        "parameters": {
            "type": "object",
            "properties": {
                "compare_with": {
                    "type": "string",
                    "enum": ["yesterday", "last_week", "last_month"],
                    "description": "Comparar con periodo anterior"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_margin_analysis",
        "description": "Obtener analisis de margenes por producto o categoria. Usa esto cuando pregunten por margen bruto, ganancias por producto, o rentabilidad.",
        "parameters": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "enum": ["product", "category"],
                    "description": "Agrupar por producto o categoria"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["margin_percent", "total_margin", "revenue"],
                    "description": "Ordenar por margen %, ganancia total, o ingresos"
                },
                "limit": {
                    "type": "integer",
                    "description": "Limitar resultados"
                }
            },
            "required": []
        }
    },
    {
        "name": "generate_proactive_insights",
        "description": "Generar insights proactivos basados en datos actuales. Usa esto cuando el admin pida sugerencias, insights, o que analices la situacion.",
        "parameters": {
            "type": "object",
            "properties": {
                "focus_area": {
                    "type": "string",
                    "enum": ["sales", "costs", "products", "operations", "all"],
                    "description": "Area de enfoque para los insights"
                }
            },
            "required": []
        }
    },
    {
        "name": "compare_periods",
        "description": "Comparar metricas entre dos periodos. Usa esto cuando pregunten 'como vamos vs ayer/semana pasada'.",
        "parameters": {
            "type": "object",
            "properties": {
                "current_period": {
                    "type": "string",
                    "enum": ["today", "this_week", "this_month"],
                    "description": "Periodo actual"
                },
                "compare_period": {
                    "type": "string",
                    "enum": ["yesterday", "last_week", "last_month"],
                    "description": "Periodo de comparacion"
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Metricas a comparar (sales, orders, ticket, food_cost)"
                }
            },
            "required": ["current_period", "compare_period"]
        }
    },

    # =========================================================================
    # HERRAMIENTAS IoT - SENSORES ESP32 MESH/ROUTER
    # =========================================================================
    {
        "name": "get_sensor_readings",
        "description": "Obtener lecturas actuales de sensores IoT (temperatura, humedad, CO2, humo). Usa esto cuando pregunten por condiciones actuales del restaurante.",
        "parameters": {
            "type": "object",
            "properties": {
                "sensor_type": {
                    "type": "string",
                    "enum": ["temperature", "humidity", "co2", "smoke", "motion", "light"],
                    "description": "Tipo de sensor especifico (opcional)"
                },
                "location": {
                    "type": "string",
                    "description": "Ubicacion: cocina, comedor, terraza, almacen, barra (opcional)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_sensor_history",
        "description": "Obtener historico de lecturas de un sensor. Usa esto cuando pregunten como ha estado la temperatura/humedad en las ultimas horas.",
        "parameters": {
            "type": "object",
            "properties": {
                "sensor_type": {
                    "type": "string",
                    "enum": ["temperature", "humidity", "co2", "smoke"],
                    "description": "Tipo de sensor a consultar"
                },
                "hours": {
                    "type": "integer",
                    "description": "Horas de historico a consultar (default: 24)"
                },
                "location": {
                    "type": "string",
                    "description": "Ubicacion especifica (opcional)"
                }
            },
            "required": ["sensor_type"]
        }
    },
    {
        "name": "get_device_status",
        "description": "Obtener estado de dispositivos IoT (nodos MESH, Router ESP32). Usa esto cuando pregunten por conectividad o estado de sensores.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "ID del dispositivo especifico (opcional)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_iot_alerts",
        "description": "Obtener alertas del sistema IoT. Usa esto cuando pregunten si hay alertas, problemas o situaciones que requieran atencion.",
        "parameters": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Horas a consultar (default: 24)"
                },
                "severity": {
                    "type": "string",
                    "enum": ["warning", "critical", "emergency"],
                    "description": "Filtrar por severidad (opcional)"
                }
            },
            "required": []
        }
    },
    {
        "name": "analyze_environment",
        "description": "Analizar condiciones ambientales completas con recomendaciones. Esta es la herramienta PRINCIPAL cuando pregunten por el ambiente, como esta el restaurante, temperatura, calidad del aire, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Ubicacion especifica a analizar (opcional)"
                },
                "include_recommendations": {
                    "type": "boolean",
                    "description": "Incluir recomendaciones de mejora (default: true)"
                }
            },
            "required": []
        }
    },
    {
        "name": "acknowledge_alert",
        "description": "Reconocer/atender una alerta del sistema IoT. Usa esto cuando el admin diga que ya atendio o reviso una alerta.",
        "parameters": {
            "type": "object",
            "properties": {
                "alert_id": {
                    "type": "string",
                    "description": "ID de la alerta a reconocer"
                }
            },
            "required": ["alert_id"]
        }
    },

    # =========================================================================
    # WHATSAPP BROADCAST
    # =========================================================================
    {
        "name": "send_whatsapp_broadcast",
        "description": "Enviar promocion o mensaje broadcast a clientes por WhatsApp. Usa esto cuando el admin quiera enviar una promocion, notificar a clientes, o hacer marketing por WhatsApp.",
        "parameters": {
            "type": "object",
            "properties": {
                "promotion_id": {
                    "type": "string",
                    "description": "ID de la promocion a enviar (opcional si se envia mensaje custom)"
                },
                "custom_message": {
                    "type": "string",
                    "description": "Mensaje personalizado (opcional, si no se usa una promocion existente)"
                },
                "audience_filter": {
                    "type": "object",
                    "description": "Filtro de audiencia para segmentar clientes",
                    "properties": {
                        "segment": {
                            "type": "string",
                            "enum": ["all", "frequent", "inactive", "new", "vip", "custom"],
                            "description": "Segmento de clientes: all (todos), frequent (frecuentes 3+ ordenes), inactive (30+ dias sin ordenar), new (1-2 ordenes), vip (alto valor), custom (filtros personalizados)"
                        },
                        "min_orders": {
                            "type": "integer",
                            "description": "Minimo de ordenes previas (para segment=custom)"
                        },
                        "max_orders": {
                            "type": "integer",
                            "description": "Maximo de ordenes (para segment=custom)"
                        },
                        "last_order_days": {
                            "type": "integer",
                            "description": "Dias desde ultima orden (para segment=custom)"
                        },
                        "min_spent": {
                            "type": "number",
                            "description": "Gasto minimo total (para segment=custom o vip)"
                        }
                    },
                    "required": ["segment"]
                },
                "personalize": {
                    "type": "boolean",
                    "description": "Si debe personalizar el mensaje para cada cliente (recomendado: true)"
                }
            },
            "required": ["audience_filter"]
        }
    }
]


# ==============================================================================
# ADMIN TOOLS CLASS
# ==============================================================================

class AdminTools:
    """
    Ejecutor de herramientas administrativas.

    Conecta con los servicios del backend:
    - menu-service: Productos, categorias, promociones
    - analytics-service: Ventas, metricas, reportes
    - order-service: Ordenes
    """

    def __init__(self):
        """Inicializar AdminTools con URLs de servicios"""
        # Obtener URLs y remover /api/v1 si está incluido para evitar duplicación
        _raw_menu_url = os.getenv('MENU_SERVICE_URL', 'http://menu-service:5011')
        self.menu_service_url = _raw_menu_url.rstrip("/").removesuffix("/api/v1")
        self.analytics_service_url = os.getenv('ANALYTICS_SERVICE_URL', 'http://reports-service:5015')
        self.order_service_url = os.getenv('ORDER_SERVICE_URL', 'http://orders-service:5012')

        # IoT Gateway para sensores y dispositivos ESP32
        self.iot_gateway_url = os.getenv('IOT_GATEWAY_URL', 'http://iot-gateway:8085')

        # Timeout para requests
        self.timeout = aiohttp.ClientTimeout(total=10)

        logger.info(f"[AdminTools] Inicializado - Menu: {self.menu_service_url}, IoT: {self.iot_gateway_url}")

    # ==========================================================================
    # HERRAMIENTAS DE VENTAS/ANALYTICS
    # ==========================================================================

    async def get_sales_report(
        self,
        period: str = "today",
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener reporte de ventas.

        Args:
            period: today, yesterday, week, month
            category: Filtrar por categoria (opcional)

        Returns:
            Dict con total_sales, order_count, avg_ticket
        """
        try:
            # Calcular fechas segun periodo
            today = datetime.now().date()

            if period == "today":
                start_date = today
                end_date = today
            elif period == "yesterday":
                start_date = today - timedelta(days=1)
                end_date = start_date
            elif period == "week":
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == "month":
                start_date = today - timedelta(days=30)
                end_date = today
            else:
                start_date = today
                end_date = today

            # Llamar al analytics service
            url = f"{self.analytics_service_url}/api/v1/sales/summary"
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            if category:
                params["category"] = category

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "period": period,
                            "total_sales": data.get("total_sales", 0),
                            "order_count": data.get("order_count", 0),
                            "avg_ticket": data.get("avg_ticket", 0),
                            "category": category
                        }

            # Fallback con datos simulados si el servicio no responde
            logger.warning("[AdminTools] Analytics service no disponible, usando datos simulados")
            return self._get_simulated_sales_report(period, category)

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_sales_report: {e}")
            return self._get_simulated_sales_report(period, category)

    def _get_simulated_sales_report(self, period: str, category: Optional[str]) -> Dict:
        """Datos simulados para desarrollo/demo"""
        import random

        base_sales = {
            "today": random.randint(8000, 15000),
            "yesterday": random.randint(7000, 14000),
            "week": random.randint(50000, 90000),
            "month": random.randint(200000, 350000)
        }

        base_orders = {
            "today": random.randint(40, 80),
            "yesterday": random.randint(35, 75),
            "week": random.randint(280, 500),
            "month": random.randint(1200, 2000)
        }

        total = base_sales.get(period, 10000)
        orders = base_orders.get(period, 50)

        return {
            "success": True,
            "period": period,
            "total_sales": total,
            "order_count": orders,
            "avg_ticket": round(total / orders, 2) if orders > 0 else 0,
            "category": category,
            "simulated": True
        }

    async def get_top_products(
        self,
        limit: int = 5,
        period: str = "week"
    ) -> Dict[str, Any]:
        """Obtener productos mas vendidos"""
        try:
            url = f"{self.analytics_service_url}/api/v1/products/top"
            params = {"limit": limit, "period": period}

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "products": data.get("products", []),
                            "period": period
                        }

            # Fallback simulado
            return {
                "success": True,
                "products": [
                    {"name": "Hamburguesa Clasica", "quantity": 145, "revenue": 14500},
                    {"name": "Tacos al Pastor", "quantity": 120, "revenue": 9600},
                    {"name": "Papas Francesas", "quantity": 98, "revenue": 4900},
                    {"name": "Refresco", "quantity": 87, "revenue": 2610},
                    {"name": "Hamburguesa BBQ", "quantity": 76, "revenue": 9880}
                ][:limit],
                "period": period,
                "simulated": True
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_top_products: {e}")
            return {"success": False, "error": str(e)}

    async def get_orders_count(
        self,
        period: str = "today",
        status: str = "all"
    ) -> Dict[str, Any]:
        """Obtener cantidad de ordenes"""
        try:
            url = f"{self.order_service_url}/api/v1/orders/count"
            params = {"period": period, "status": status}

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"success": True, **data}

            # Fallback simulado
            import random
            counts = {
                "today": {"total": random.randint(40, 80), "pending": random.randint(2, 8), "completed": random.randint(35, 70)},
                "yesterday": {"total": random.randint(35, 75), "pending": 0, "completed": random.randint(35, 75)},
                "week": {"total": random.randint(280, 500), "pending": random.randint(5, 15), "completed": random.randint(260, 480)},
                "month": {"total": random.randint(1200, 2000), "pending": random.randint(10, 30), "completed": random.randint(1100, 1900)}
            }

            data = counts.get(period, counts["today"])
            return {
                "success": True,
                "period": period,
                "status_filter": status,
                **data,
                "simulated": True
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_orders_count: {e}")
            return {"success": False, "error": str(e)}

    async def get_hourly_sales(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Obtener ventas por hora"""
        try:
            url = f"{self.analytics_service_url}/api/v1/sales/hourly"
            params = {}
            if date:
                params["date"] = date

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return {"success": True, **(await response.json())}

            # Simulado
            import random
            hourly = {}
            for hour in range(8, 23):
                # Pico en horas de comida
                if hour in [13, 14, 20, 21]:
                    hourly[f"{hour}:00"] = random.randint(800, 1500)
                elif hour in [12, 15, 19, 22]:
                    hourly[f"{hour}:00"] = random.randint(500, 900)
                else:
                    hourly[f"{hour}:00"] = random.randint(100, 400)

            peak_hour = max(hourly, key=hourly.get)

            return {
                "success": True,
                "date": date or datetime.now().date().isoformat(),
                "hourly_sales": hourly,
                "peak_hour": peak_hour,
                "peak_sales": hourly[peak_hour],
                "simulated": True
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_hourly_sales: {e}")
            return {"success": False, "error": str(e)}

    async def get_average_ticket(self, period: str = "today") -> Dict[str, Any]:
        """Obtener ticket promedio"""
        report = await self.get_sales_report(period)
        return {
            "success": True,
            "period": period,
            "avg_ticket": report.get("avg_ticket", 0),
            "order_count": report.get("order_count", 0)
        }

    async def generate_daily_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Generar reporte diario completo"""
        try:
            # Obtener todas las metricas
            sales = await self.get_sales_report("today")
            top_products = await self.get_top_products(5, "today")
            hourly = await self.get_hourly_sales(date)
            orders = await self.get_orders_count("today")

            return {
                "success": True,
                "date": date or datetime.now().date().isoformat(),
                "summary": {
                    "total_sales": sales.get("total_sales", 0),
                    "order_count": orders.get("total", 0),
                    "avg_ticket": sales.get("avg_ticket", 0),
                    "pending_orders": orders.get("pending", 0)
                },
                "top_products": top_products.get("products", [])[:3],
                "peak_hour": hourly.get("peak_hour"),
                "peak_sales": hourly.get("peak_sales")
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en generate_daily_report: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================================================
    # HERRAMIENTAS DE PROMOCIONES
    # ==========================================================================

    async def create_promotion(
        self,
        name: str,
        promotion_type: str,
        discount_value: Optional[float] = None,
        products: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        days: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crear una nueva promocion"""
        try:
            url = f"{self.menu_service_url}/api/v1/promotions"

            payload = {
                "name": name,
                "promotion_type": promotion_type,
                "is_active": True
            }

            if discount_value:
                payload["discount_value"] = discount_value

            if start_time:
                payload["start_time"] = start_time

            if end_time:
                payload["end_time"] = end_time

            if days:
                payload["days_of_week"] = days

            # Generar voice_pitch automatico
            if promotion_type == "2x1":
                payload["voice_pitch"] = f"Aprovecha nuestro {name}, lleva dos y paga uno."
            elif promotion_type == "percentage" and discount_value:
                payload["voice_pitch"] = f"Tenemos {name} con {int(discount_value)}% de descuento."
            elif promotion_type == "fixed" and discount_value:
                payload["voice_pitch"] = f"Con {name} te ahorras ${int(discount_value)} pesos."

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        return {
                            "success": True,
                            "message": f"Promocion '{name}' creada exitosamente",
                            "promotion_id": data.get("id"),
                            "promotion": data
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Error al crear promocion: {error_text}"
                        }

        except aiohttp.ClientError as e:
            logger.error(f"[AdminTools] Error conectando a menu-service: {e}")
            return {
                "success": False,
                "error": "No se pudo conectar al servicio de menu"
            }
        except Exception as e:
            logger.error(f"[AdminTools] Error en create_promotion: {e}")
            return {"success": False, "error": str(e)}

    async def toggle_promotion(
        self,
        promotion_name: str,
        active: bool
    ) -> Dict[str, Any]:
        """Activar o desactivar una promocion"""
        try:
            # Primero buscar la promocion por nombre
            list_url = f"{self.menu_service_url}/api/v1/promotions"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(list_url) as response:
                    if response.status == 200:
                        promotions = await response.json()
                        promo = next(
                            (p for p in promotions if p["name"].lower() == promotion_name.lower()),
                            None
                        )

                        if not promo:
                            return {
                                "success": False,
                                "error": f"No se encontro la promocion '{promotion_name}'"
                            }

                        # Hacer toggle
                        toggle_url = f"{self.menu_service_url}/api/v1/promotions/{promo['id']}/toggle"
                        async with session.patch(toggle_url, params={"is_active": active}) as toggle_response:
                            if toggle_response.status == 200:
                                status_text = "activada" if active else "desactivada"
                                return {
                                    "success": True,
                                    "message": f"Promocion '{promotion_name}' {status_text}",
                                    "promotion_id": promo["id"],
                                    "is_active": active
                                }

            return {"success": False, "error": "Error al cambiar estado de promocion"}

        except Exception as e:
            logger.error(f"[AdminTools] Error en toggle_promotion: {e}")
            return {"success": False, "error": str(e)}

    async def list_promotions(self, active_only: bool = True) -> Dict[str, Any]:
        """Listar promociones"""
        try:
            url = f"{self.menu_service_url}/api/v1/promotions"
            params = {"active_only": active_only} if active_only else {}

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        promotions = await response.json()
                        return {
                            "success": True,
                            "count": len(promotions),
                            "promotions": [
                                {
                                    "name": p["name"],
                                    "type": p["promotion_type"],
                                    "is_active": p["is_active"],
                                    "discount": p.get("discount_value")
                                }
                                for p in promotions
                            ]
                        }

            return {
                "success": True,
                "count": 0,
                "promotions": [],
                "message": "No hay promociones registradas"
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en list_promotions: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================================================
    # HERRAMIENTAS DE MENU/PRODUCTOS
    # ==========================================================================

    async def toggle_product(
        self,
        product_name: str,
        available: bool
    ) -> Dict[str, Any]:
        """Activar o desactivar un producto"""
        try:
            # Buscar producto por nombre
            search_url = f"{self.menu_service_url}/api/v1/products"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(search_url, params={"search": product_name}) as response:
                    if response.status == 200:
                        products = await response.json()
                        product = next(
                            (p for p in products if product_name.lower() in p["name"].lower()),
                            None
                        )

                        if not product:
                            return {
                                "success": False,
                                "error": f"No se encontro el producto '{product_name}'"
                            }

                        # Actualizar disponibilidad
                        update_url = f"{self.menu_service_url}/api/v1/products/{product['id']}/availability"
                        async with session.patch(update_url, params={"is_available": available}) as update_response:
                            if update_response.status == 200:
                                status_text = "disponible" if available else "agotado"
                                return {
                                    "success": True,
                                    "message": f"'{product['name']}' marcado como {status_text}",
                                    "product_id": product["id"],
                                    "is_available": available
                                }

            return {"success": False, "error": "Error al actualizar producto"}

        except Exception as e:
            logger.error(f"[AdminTools] Error en toggle_product: {e}")
            return {"success": False, "error": str(e)}

    async def update_product_price(
        self,
        product_name: str,
        new_price: float
    ) -> Dict[str, Any]:
        """Actualizar precio de un producto"""
        try:
            search_url = f"{self.menu_service_url}/api/v1/products"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(search_url, params={"search": product_name}) as response:
                    if response.status == 200:
                        products = await response.json()
                        product = next(
                            (p for p in products if product_name.lower() in p["name"].lower()),
                            None
                        )

                        if not product:
                            return {
                                "success": False,
                                "error": f"No se encontro el producto '{product_name}'"
                            }

                        old_price = product.get("price", 0)

                        # Actualizar precio
                        update_url = f"{self.menu_service_url}/api/v1/products/{product['id']}"
                        async with session.put(update_url, json={"price": new_price}) as update_response:
                            if update_response.status == 200:
                                return {
                                    "success": True,
                                    "message": f"Precio de '{product['name']}' actualizado de ${old_price} a ${new_price}",
                                    "product_id": product["id"],
                                    "old_price": old_price,
                                    "new_price": new_price
                                }

            return {"success": False, "error": "Error al actualizar precio"}

        except Exception as e:
            logger.error(f"[AdminTools] Error en update_product_price: {e}")
            return {"success": False, "error": str(e)}

    async def get_unavailable_products(self) -> Dict[str, Any]:
        """Obtener productos no disponibles"""
        try:
            url = f"{self.menu_service_url}/api/v1/products"
            params = {"available_only": False}

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        products = await response.json()
                        unavailable = [p for p in products if not p.get("is_available", True)]

                        return {
                            "success": True,
                            "count": len(unavailable),
                            "products": [
                                {"name": p["name"], "category": p.get("category", {}).get("name")}
                                for p in unavailable
                            ]
                        }

            return {"success": True, "count": 0, "products": []}

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_unavailable_products: {e}")
            return {"success": False, "error": str(e)}

    async def create_product(
        self,
        name: str,
        price: float,
        description: Optional[str] = None,
        category: Optional[str] = None,
        ingredients: Optional[str] = None,
        spice_level: int = 0,
        preparation_time: int = 15,
        cost: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Crear un nuevo producto en el menu.

        Args:
            name: Nombre del producto
            price: Precio en pesos
            description: Descripcion del producto
            category: Nombre de la categoria
            ingredients: Ingredientes principales
            spice_level: Nivel de picante (0-3)
            preparation_time: Tiempo de preparacion en minutos
            cost: Costo de preparacion

        Returns:
            Dict con resultado de la operacion
        """
        try:
            # Primero, buscar la categoria si se proporciona
            category_id = None
            if category:
                categories_url = f"{self.menu_service_url}/api/v1/categories"
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(categories_url) as response:
                        if response.status == 200:
                            categories = await response.json()
                            # Buscar categoria por nombre (case insensitive)
                            for cat in categories:
                                if cat["name"].lower() == category.lower():
                                    category_id = cat["id"]
                                    break

                            # Si no se encuentra, crear la categoria
                            if category_id is None:
                                logger.info(f"[AdminTools] Categoria '{category}' no encontrada, creando...")
                                create_cat_url = f"{self.menu_service_url}/api/v1/categories"
                                cat_payload = {"name": category, "is_active": True}
                                async with session.post(create_cat_url, json=cat_payload) as cat_response:
                                    if cat_response.status in [200, 201]:
                                        cat_data = await cat_response.json()
                                        category_id = cat_data.get("id")
                                        logger.info(f"[AdminTools] Categoria '{category}' creada con ID: {category_id}")

            # Construir payload del producto
            payload = {
                "name": name,
                "price": price,
                "is_available": True,
                "spice_level": spice_level,
                "preparation_time_minutes": preparation_time,
                "popularity": 3,  # Default medio
                "profitability": "media"
            }

            if description:
                payload["description"] = description

            if category_id:
                payload["category_id"] = category_id

            if ingredients:
                payload["ingredients"] = ingredients

            if cost:
                payload["cost"] = cost
                # Calcular rentabilidad basada en margen
                margin_percent = ((price - cost) / price) * 100 if price > 0 else 0
                if margin_percent >= 60:
                    payload["profitability"] = "alta"
                elif margin_percent >= 40:
                    payload["profitability"] = "media"
                else:
                    payload["profitability"] = "baja"

            # Crear el producto
            url = f"{self.menu_service_url}/api/v1/products"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        logger.info(f"[AdminTools] Producto '{name}' creado exitosamente con ID: {data.get('id')}")

                        return {
                            "success": True,
                            "message": f"Producto '{name}' creado exitosamente",
                            "product_id": data.get("id"),
                            "product_uuid": data.get("uuid"),
                            "product": {
                                "name": data.get("name"),
                                "price": float(data.get("price", 0)),
                                "category": category,
                                "description": data.get("description"),
                                "is_available": data.get("is_available", True)
                            }
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"[AdminTools] Error al crear producto: {error_text}")
                        return {
                            "success": False,
                            "error": f"Error al crear producto: {error_text}"
                        }

        except aiohttp.ClientError as e:
            logger.error(f"[AdminTools] Error conectando a menu-service: {e}")
            return {
                "success": False,
                "error": "No se pudo conectar al servicio de menu"
            }
        except Exception as e:
            logger.error(f"[AdminTools] Error en create_product: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================================================
    # ESTRATEGIA 3: HERRAMIENTAS DE ANALISIS AVANZADO
    # ==========================================================================

    async def analyze_food_cost(
        self,
        period: str = "today",
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Analizar food cost con interpretacion y recomendaciones.

        Returns:
            Analisis completo con:
            - food_cost_percent: Porcentaje de food cost
            - classification: excelente/bueno/aceptable/critico
            - trend: tendencia vs periodo anterior
            - top_cost_items: Productos con mayor costo
            - recommendations: Lista de recomendaciones (si aplica)
        """
        try:
            # Obtener datos de ventas y costos
            sales_data = await self.get_sales_report(period)
            top_products = await self.get_top_products(10, period)

            total_sales = sales_data.get("total_sales", 0)

            # Simular costos (en produccion vendria del servicio de inventario)
            import random
            estimated_cost_percent = random.uniform(28, 42)  # Entre 28% y 42%
            total_cost = total_sales * (estimated_cost_percent / 100)
            gross_margin = 100 - estimated_cost_percent

            # Clasificar food cost
            if estimated_cost_percent <= 28:
                classification = "excelente"
                health_status = "🟢"
            elif estimated_cost_percent <= 32:
                classification = "bueno"
                health_status = "🟢"
            elif estimated_cost_percent <= 35:
                classification = "aceptable"
                health_status = "🟡"
            elif estimated_cost_percent <= 40:
                classification = "alto"
                health_status = "🟠"
            else:
                classification = "critico"
                health_status = "🔴"

            # Identificar productos con alto costo (simulado)
            high_cost_items = []
            products = top_products.get("products", [])
            for p in products[:5]:
                item_cost_percent = random.uniform(25, 50)
                if item_cost_percent > 35:
                    high_cost_items.append({
                        "name": p["name"],
                        "cost_percent": round(item_cost_percent, 1),
                        "revenue": p.get("revenue", 0),
                        "suggestion": "Revisar proveedores o ajustar precio"
                    })

            # Generar recomendaciones
            recommendations = []
            if include_recommendations:
                if estimated_cost_percent > 35:
                    recommendations.append({
                        "priority": "alta",
                        "action": "Negociar con proveedores principales",
                        "potential_saving": f"${int(total_cost * 0.05):,} (5% reduccion)"
                    })
                if estimated_cost_percent > 40:
                    recommendations.append({
                        "priority": "alta",
                        "action": "Revisar porciones y mermas en cocina",
                        "potential_saving": f"${int(total_cost * 0.08):,} (8% reduccion)"
                    })
                if high_cost_items:
                    recommendations.append({
                        "priority": "media",
                        "action": f"Ajustar precios de {len(high_cost_items)} productos con bajo margen",
                        "potential_saving": "Mejorar margen 3-5%"
                    })
                if estimated_cost_percent < 30:
                    recommendations.append({
                        "priority": "baja",
                        "action": "Excelente control de costos! Mantener practicas actuales",
                        "potential_saving": "N/A"
                    })

            return {
                "success": True,
                "period": period,
                "food_cost_percent": round(estimated_cost_percent, 1),
                "gross_margin_percent": round(gross_margin, 1),
                "total_sales": total_sales,
                "total_cost": round(total_cost, 2),
                "classification": classification,
                "health_status": health_status,
                "high_cost_items": high_cost_items,
                "recommendations": recommendations,
                "industry_benchmark": {
                    "excellent": "< 28%",
                    "good": "28-32%",
                    "acceptable": "32-35%",
                    "needs_attention": "35-40%",
                    "critical": "> 40%"
                }
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en analyze_food_cost: {e}")
            return {"success": False, "error": str(e)}

    async def analyze_product_performance(
        self,
        period: str = "week",
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analizar productos usando matriz BCG simplificada.

        Clasifica productos en:
        - ⭐ ESTRELLAS: Alto volumen + Alto margen (promocionar)
        - 🐄 VACAS: Alto volumen + Bajo margen (optimizar costos)
        - ❓ INTERROGANTES: Bajo volumen + Alto margen (evaluar promocion)
        - 🐕 PERROS: Bajo volumen + Bajo margen (considerar retirar)
        """
        try:
            top_products = await self.get_top_products(20, period)
            products = top_products.get("products", [])

            if not products:
                return {
                    "success": True,
                    "message": "No hay suficientes datos de productos",
                    "stars": [], "cows": [], "question_marks": [], "dogs": []
                }

            import random

            # Calcular promedios para clasificacion
            avg_quantity = sum(p.get("quantity", 0) for p in products) / len(products) if products else 0

            stars = []
            cows = []
            question_marks = []
            dogs = []

            for p in products:
                qty = p.get("quantity", 0)
                revenue = p.get("revenue", 0)

                # Simular margen (en produccion vendria de costos reales)
                margin_percent = random.uniform(30, 75)
                is_high_volume = qty >= avg_quantity
                is_high_margin = margin_percent >= 50

                product_info = {
                    "name": p["name"],
                    "quantity": qty,
                    "revenue": revenue,
                    "margin_percent": round(margin_percent, 1)
                }

                if is_high_volume and is_high_margin:
                    product_info["recommendation"] = "Mantener y promocionar"
                    stars.append(product_info)
                elif is_high_volume and not is_high_margin:
                    product_info["recommendation"] = "Negociar costos o aumentar precio"
                    cows.append(product_info)
                elif not is_high_volume and is_high_margin:
                    product_info["recommendation"] = "Invertir en promocion"
                    question_marks.append(product_info)
                else:
                    product_info["recommendation"] = "Evaluar retiro del menu"
                    dogs.append(product_info)

            return {
                "success": True,
                "period": period,
                "total_products_analyzed": len(products),
                "avg_quantity_threshold": round(avg_quantity, 0),
                "stars": stars[:5],  # ⭐ Los mejores
                "cows": cows[:5],  # 🐄 Volumen pero bajo margen
                "question_marks": question_marks[:5],  # ❓ Potencial
                "dogs": dogs[:5],  # 🐕 Candidatos a retirar
                "summary": {
                    "stars_count": len(stars),
                    "cows_count": len(cows),
                    "question_marks_count": len(question_marks),
                    "dogs_count": len(dogs)
                },
                "action_items": [
                    f"⭐ {len(stars)} productos estrella para destacar en menu",
                    f"🐄 {len(cows)} vacas de efectivo - revisar costos",
                    f"❓ {len(question_marks)} con potencial - evaluar promocion",
                    f"🐕 {len(dogs)} perros - considerar retirar"
                ]
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en analyze_product_performance: {e}")
            return {"success": False, "error": str(e)}

    async def analyze_sales_trend(
        self,
        compare_with: str = "yesterday"
    ) -> Dict[str, Any]:
        """
        Analizar tendencia de ventas con proyeccion.
        """
        try:
            current = await self.get_sales_report("today")
            hourly = await self.get_hourly_sales()

            # Obtener periodo de comparacion
            if compare_with == "yesterday":
                compare_data = await self.get_sales_report("yesterday")
            elif compare_with == "last_week":
                compare_data = await self.get_sales_report("week")
                compare_data["total_sales"] = compare_data.get("total_sales", 0) / 7
            else:
                compare_data = await self.get_sales_report("month")
                compare_data["total_sales"] = compare_data.get("total_sales", 0) / 30

            current_sales = current.get("total_sales", 0)
            compare_sales = compare_data.get("total_sales", 0)

            if compare_sales > 0:
                change_percent = ((current_sales - compare_sales) / compare_sales) * 100
            else:
                change_percent = 0

            # Determinar tendencia
            if change_percent > 15:
                trend = "fuerte_alza"
                trend_emoji = "📈🚀"
                interpretation = "Excelente dia! Ventas muy por encima del promedio"
            elif change_percent > 5:
                trend = "alza"
                trend_emoji = "📈"
                interpretation = "Buen ritmo de ventas, por encima del periodo anterior"
            elif change_percent > -5:
                trend = "estable"
                trend_emoji = "➡️"
                interpretation = "Ventas estables, en linea con el periodo anterior"
            elif change_percent > -15:
                trend = "baja"
                trend_emoji = "📉"
                interpretation = "Ventas por debajo del periodo anterior"
            else:
                trend = "fuerte_baja"
                trend_emoji = "📉⚠️"
                interpretation = "Atencion: Ventas significativamente por debajo"

            # Proyeccion del dia
            current_hour = datetime.now().hour
            if current_hour >= 8:
                hours_passed = current_hour - 8
                hours_remaining = max(0, 22 - current_hour)
                if hours_passed > 0:
                    hourly_rate = current_sales / hours_passed
                    projected_total = current_sales + (hourly_rate * hours_remaining)
                else:
                    projected_total = current_sales
            else:
                projected_total = current_sales

            return {
                "success": True,
                "current_sales": current_sales,
                "compare_sales": compare_sales,
                "compare_period": compare_with,
                "change_percent": round(change_percent, 1),
                "trend": trend,
                "trend_emoji": trend_emoji,
                "interpretation": interpretation,
                "projection": {
                    "estimated_end_of_day": round(projected_total, 2),
                    "confidence": "media" if current_hour < 14 else "alta",
                    "based_on_hours": current_hour - 8 if current_hour >= 8 else 0
                },
                "peak_hour": hourly.get("peak_hour"),
                "peak_sales": hourly.get("peak_sales")
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en analyze_sales_trend: {e}")
            return {"success": False, "error": str(e)}

    async def get_margin_analysis(
        self,
        group_by: str = "product",
        sort_by: str = "margin_percent",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Analisis de margenes por producto o categoria.
        """
        try:
            import random

            top_products = await self.get_top_products(limit, "week")
            products = top_products.get("products", [])

            margin_data = []
            for p in products:
                revenue = p.get("revenue", 0)
                # Simular costo (30-55% del precio de venta)
                cost_percent = random.uniform(30, 55)
                cost = revenue * (cost_percent / 100)
                margin = revenue - cost
                margin_percent = 100 - cost_percent

                margin_data.append({
                    "name": p["name"],
                    "quantity_sold": p.get("quantity", 0),
                    "revenue": revenue,
                    "estimated_cost": round(cost, 2),
                    "gross_margin": round(margin, 2),
                    "margin_percent": round(margin_percent, 1),
                    "classification": "alto" if margin_percent >= 55 else "medio" if margin_percent >= 45 else "bajo"
                })

            # Ordenar
            if sort_by == "margin_percent":
                margin_data.sort(key=lambda x: x["margin_percent"], reverse=True)
            elif sort_by == "total_margin":
                margin_data.sort(key=lambda x: x["gross_margin"], reverse=True)
            else:
                margin_data.sort(key=lambda x: x["revenue"], reverse=True)

            # Calcular totales
            total_revenue = sum(p["revenue"] for p in margin_data)
            total_margin = sum(p["gross_margin"] for p in margin_data)
            avg_margin_percent = (total_margin / total_revenue * 100) if total_revenue > 0 else 0

            # Identificar top y bottom performers
            high_margin = [p for p in margin_data if p["margin_percent"] >= 55]
            low_margin = [p for p in margin_data if p["margin_percent"] < 45]

            return {
                "success": True,
                "group_by": group_by,
                "sorted_by": sort_by,
                "products": margin_data[:limit],
                "summary": {
                    "total_revenue": total_revenue,
                    "total_gross_margin": round(total_margin, 2),
                    "avg_margin_percent": round(avg_margin_percent, 1),
                    "high_margin_count": len(high_margin),
                    "low_margin_count": len(low_margin)
                },
                "insights": [
                    f"{len(high_margin)} productos con margen alto (>55%)",
                    f"{len(low_margin)} productos con margen bajo (<45%) que requieren atencion",
                    f"Margen promedio: {round(avg_margin_percent, 1)}%"
                ]
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_margin_analysis: {e}")
            return {"success": False, "error": str(e)}

    async def generate_proactive_insights(
        self,
        focus_area: str = "all"
    ) -> Dict[str, Any]:
        """
        Generar insights proactivos basados en analisis de datos.
        """
        try:
            # Recopilar datos
            sales = await self.get_sales_report("today")
            yesterday = await self.get_sales_report("yesterday")
            top_products = await self.get_top_products(5)
            hourly = await self.get_hourly_sales()
            food_cost = await self.analyze_food_cost(include_recommendations=False)

            insights = []
            action_items = []

            # INSIGHTS DE VENTAS
            if focus_area in ["sales", "all"]:
                current_sales = sales.get("total_sales", 0)
                yesterday_sales = yesterday.get("total_sales", 0)

                if yesterday_sales > 0:
                    change = ((current_sales - yesterday_sales) / yesterday_sales) * 100

                    if change > 20:
                        insights.append({
                            "type": "positive",
                            "category": "ventas",
                            "message": f"🚀 Excelente dia! Ventas {change:.0f}% arriba vs ayer",
                            "detail": f"${current_sales:,.0f} hoy vs ${yesterday_sales:,.0f} ayer"
                        })
                    elif change < -15:
                        insights.append({
                            "type": "warning",
                            "category": "ventas",
                            "message": f"⚠️ Ventas {abs(change):.0f}% abajo vs ayer",
                            "detail": "Considera activar promocion de impulso"
                        })
                        action_items.append("Evaluar promocion flash para impulsar ventas")

            # INSIGHTS DE COSTOS
            if focus_area in ["costs", "all"]:
                fc_percent = food_cost.get("food_cost_percent", 0)
                if fc_percent > 38:
                    insights.append({
                        "type": "alert",
                        "category": "costos",
                        "message": f"🔴 Food cost alto: {fc_percent:.1f}%",
                        "detail": "Objetivo: mantener por debajo de 35%"
                    })
                    action_items.append("Revisar precios de insumos y negociar con proveedores")
                elif fc_percent < 30:
                    insights.append({
                        "type": "positive",
                        "category": "costos",
                        "message": f"✅ Excelente control de costos: {fc_percent:.1f}%",
                        "detail": "Mantener practicas actuales"
                    })

            # INSIGHTS DE PRODUCTOS
            if focus_area in ["products", "all"]:
                products = top_products.get("products", [])
                if products:
                    top_product = products[0]
                    insights.append({
                        "type": "info",
                        "category": "productos",
                        "message": f"🏆 Top del dia: {top_product['name']}",
                        "detail": f"{top_product['quantity']} vendidos (${top_product['revenue']:,})"
                    })

            # INSIGHTS OPERATIVOS
            if focus_area in ["operations", "all"]:
                current_hour = datetime.now().hour
                peak_hour = hourly.get("peak_hour", "")

                if peak_hour:
                    peak_hour_int = int(peak_hour.split(":")[0])
                    hours_to_peak = peak_hour_int - current_hour

                    if 0 < hours_to_peak <= 2:
                        insights.append({
                            "type": "info",
                            "category": "operaciones",
                            "message": f"⏰ Hora pico en {hours_to_peak}h ({peak_hour})",
                            "detail": "Preparar personal y cocina"
                        })
                        action_items.append(f"Asegurar equipo listo para hora pico ({peak_hour})")

            return {
                "success": True,
                "focus_area": focus_area,
                "generated_at": datetime.now().isoformat(),
                "insights": insights,
                "action_items": action_items,
                "summary": f"{len(insights)} insights generados, {len(action_items)} acciones sugeridas"
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en generate_proactive_insights: {e}")
            return {"success": False, "error": str(e)}

    async def compare_periods(
        self,
        current_period: str,
        compare_period: str,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Comparar metricas entre dos periodos.
        """
        try:
            metrics = metrics or ["sales", "orders", "ticket"]

            # Mapear periodos
            period_map = {
                "today": "today",
                "this_week": "week",
                "this_month": "month",
                "yesterday": "yesterday",
                "last_week": "week",
                "last_month": "month"
            }

            current_data = await self.get_sales_report(period_map.get(current_period, "today"))
            compare_data = await self.get_sales_report(period_map.get(compare_period, "yesterday"))

            comparison = {}

            if "sales" in metrics:
                current_sales = current_data.get("total_sales", 0)
                compare_sales = compare_data.get("total_sales", 0)
                change = ((current_sales - compare_sales) / compare_sales * 100) if compare_sales > 0 else 0
                comparison["sales"] = {
                    "current": current_sales,
                    "previous": compare_sales,
                    "change_percent": round(change, 1),
                    "trend": "up" if change > 0 else "down" if change < 0 else "stable"
                }

            if "orders" in metrics:
                current_orders = current_data.get("order_count", 0)
                compare_orders = compare_data.get("order_count", 0)
                change = ((current_orders - compare_orders) / compare_orders * 100) if compare_orders > 0 else 0
                comparison["orders"] = {
                    "current": current_orders,
                    "previous": compare_orders,
                    "change_percent": round(change, 1),
                    "trend": "up" if change > 0 else "down" if change < 0 else "stable"
                }

            if "ticket" in metrics:
                current_ticket = current_data.get("avg_ticket", 0)
                compare_ticket = compare_data.get("avg_ticket", 0)
                change = ((current_ticket - compare_ticket) / compare_ticket * 100) if compare_ticket > 0 else 0
                comparison["ticket"] = {
                    "current": current_ticket,
                    "previous": compare_ticket,
                    "change_percent": round(change, 1),
                    "trend": "up" if change > 0 else "down" if change < 0 else "stable"
                }

            # Generar resumen
            positive_metrics = [k for k, v in comparison.items() if v["trend"] == "up"]
            negative_metrics = [k for k, v in comparison.items() if v["trend"] == "down"]

            return {
                "success": True,
                "current_period": current_period,
                "compare_period": compare_period,
                "comparison": comparison,
                "summary": {
                    "improving": positive_metrics,
                    "declining": negative_metrics,
                    "overall_trend": "positive" if len(positive_metrics) > len(negative_metrics) else "negative" if len(negative_metrics) > len(positive_metrics) else "mixed"
                }
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en compare_periods: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================================================
    # HERRAMIENTAS IoT - SENSORES Y DISPOSITIVOS ESP32
    # ==========================================================================

    async def get_sensor_readings(
        self,
        sensor_type: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener lecturas actuales de sensores IoT.

        Args:
            sensor_type: Tipo de sensor (temperature, humidity, co2, smoke, etc.)
            location: Ubicacion (cocina, comedor, terraza, almacen)

        Returns:
            Lecturas actuales de sensores
        """
        try:
            url = f"{self.iot_gateway_url}/api/sensors/latest"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        readings = data.get("readings", [])

                        # Filtrar por tipo si se especifica
                        if sensor_type:
                            readings = [r for r in readings if r.get("sensor_type") == sensor_type]

                        # Filtrar por ubicacion si se especifica
                        if location:
                            readings = [r for r in readings if location.lower() in r.get("location", "").lower()]

                        # Agrupar por tipo de sensor
                        by_type = {}
                        for r in readings:
                            stype = r.get("sensor_type", "unknown")
                            if stype not in by_type:
                                by_type[stype] = []
                            by_type[stype].append({
                                "value": r.get("value"),
                                "unit": r.get("unit"),
                                "location": r.get("location"),
                                "device_id": r.get("device_id"),
                                "timestamp": r.get("timestamp")
                            })

                        return {
                            "success": True,
                            "readings_count": len(readings),
                            "by_sensor_type": by_type,
                            "filters_applied": {
                                "sensor_type": sensor_type,
                                "location": location
                            }
                        }

            # Fallback con datos simulados
            return self._get_simulated_sensor_readings(sensor_type, location)

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_sensor_readings: {e}")
            return self._get_simulated_sensor_readings(sensor_type, location)

    def _get_simulated_sensor_readings(
        self,
        sensor_type: Optional[str],
        location: Optional[str]
    ) -> Dict[str, Any]:
        """Datos simulados de sensores para desarrollo/demo"""
        import random

        locations = ["cocina", "comedor", "terraza", "almacen", "barra"]

        simulated = {
            "temperature": [
                {"value": round(random.uniform(22, 28), 1), "unit": "°C", "location": loc, "status": "normal"}
                for loc in locations
            ],
            "humidity": [
                {"value": round(random.uniform(45, 70), 1), "unit": "%", "location": loc, "status": "normal"}
                for loc in locations
            ],
            "co2": [
                {"value": random.randint(400, 800), "unit": "ppm", "location": loc, "status": "normal"}
                for loc in ["cocina", "comedor"]
            ],
            "smoke": [
                {"value": random.randint(0, 15), "unit": "ppm", "location": "cocina", "status": "normal"}
            ]
        }

        # Simular alguna alerta ocasionalmente
        if random.random() < 0.2:
            simulated["temperature"][0]["value"] = round(random.uniform(32, 38), 1)
            simulated["temperature"][0]["status"] = "warning"

        result = simulated
        if sensor_type and sensor_type in simulated:
            result = {sensor_type: simulated[sensor_type]}

        if location:
            for stype in result:
                result[stype] = [r for r in result[stype] if location.lower() in r.get("location", "").lower()]

        return {
            "success": True,
            "by_sensor_type": result,
            "simulated": True,
            "filters_applied": {"sensor_type": sensor_type, "location": location}
        }

    async def get_sensor_history(
        self,
        sensor_type: str,
        hours: int = 24,
        device_id: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener historico de lecturas de un sensor.

        Args:
            sensor_type: Tipo de sensor (temperature, humidity, co2, etc.)
            hours: Horas de historico (default: 24)
            device_id: ID del dispositivo especifico (opcional)
            location: Ubicacion (opcional)

        Returns:
            Historico con estadisticas y tendencias
        """
        try:
            url = f"{self.iot_gateway_url}/api/sensors/{sensor_type}/history"
            params = {"hours": hours}
            if device_id:
                params["device_id"] = device_id

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        readings = data.get("readings", [])

                        if readings:
                            values = [r.get("value", 0) for r in readings]
                            return {
                                "success": True,
                                "sensor_type": sensor_type,
                                "hours": hours,
                                "readings_count": len(readings),
                                "statistics": {
                                    "min": round(min(values), 1),
                                    "max": round(max(values), 1),
                                    "avg": round(sum(values) / len(values), 1),
                                    "current": round(values[-1], 1) if values else None
                                },
                                "trend": self._calculate_trend(values),
                                "readings": readings[-10:]  # Ultimas 10 lecturas
                            }

            # Fallback simulado
            return self._get_simulated_sensor_history(sensor_type, hours)

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_sensor_history: {e}")
            return self._get_simulated_sensor_history(sensor_type, hours)

    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calcular tendencia de valores"""
        if len(values) < 2:
            return {"direction": "stable", "change_percent": 0}

        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

        if first_half > 0:
            change = ((second_half - first_half) / first_half) * 100
        else:
            change = 0

        if change > 5:
            direction = "increasing"
        elif change < -5:
            direction = "decreasing"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "change_percent": round(change, 1)
        }

    def _get_simulated_sensor_history(self, sensor_type: str, hours: int) -> Dict[str, Any]:
        """Historico simulado de sensores"""
        import random

        base_values = {
            "temperature": (24, 3),  # media, desviacion
            "humidity": (55, 10),
            "co2": (550, 150),
            "smoke": (5, 3)
        }

        mean, std = base_values.get(sensor_type, (50, 10))
        values = [max(0, round(random.gauss(mean, std), 1)) for _ in range(hours)]

        return {
            "success": True,
            "sensor_type": sensor_type,
            "hours": hours,
            "readings_count": len(values),
            "statistics": {
                "min": round(min(values), 1),
                "max": round(max(values), 1),
                "avg": round(sum(values) / len(values), 1),
                "current": values[-1]
            },
            "trend": self._calculate_trend(values),
            "simulated": True
        }

    async def get_device_status(
        self,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener estado de dispositivos IoT (MESH nodes, Router).

        Args:
            device_id: ID especifico del dispositivo (opcional)

        Returns:
            Estado de dispositivos con conectividad y metricas
        """
        try:
            if device_id:
                url = f"{self.iot_gateway_url}/api/devices/{device_id}"
            else:
                url = f"{self.iot_gateway_url}/api/devices"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        devices = data if isinstance(data, list) else [data]

                        online = [d for d in devices if d.get("is_online", False)]
                        offline = [d for d in devices if not d.get("is_online", False)]

                        return {
                            "success": True,
                            "total_devices": len(devices),
                            "online": len(online),
                            "offline": len(offline),
                            "health_status": "healthy" if len(offline) == 0 else "degraded" if len(offline) < len(online) else "critical",
                            "devices": [
                                {
                                    "device_id": d.get("device_id"),
                                    "device_type": d.get("device_type"),
                                    "location": d.get("location"),
                                    "is_online": d.get("is_online"),
                                    "rssi": d.get("rssi"),
                                    "battery_level": d.get("battery_level"),
                                    "firmware_version": d.get("firmware_version"),
                                    "last_seen": d.get("last_seen")
                                }
                                for d in devices
                            ]
                        }

            # Fallback simulado
            return self._get_simulated_device_status()

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_device_status: {e}")
            return self._get_simulated_device_status()

    def _get_simulated_device_status(self) -> Dict[str, Any]:
        """Estado simulado de dispositivos"""
        import random

        devices = [
            {"device_id": "esp32-router-001", "device_type": "router", "location": "entrada", "is_online": True},
            {"device_id": "mesh-node-001", "device_type": "mesh_node", "location": "cocina", "is_online": True},
            {"device_id": "mesh-node-002", "device_type": "mesh_node", "location": "comedor", "is_online": True},
            {"device_id": "mesh-node-003", "device_type": "mesh_node", "location": "terraza", "is_online": random.random() > 0.1},
            {"device_id": "mesh-node-004", "device_type": "mesh_node", "location": "almacen", "is_online": True},
            {"device_id": "mesh-node-005", "device_type": "mesh_node", "location": "barra", "is_online": True}
        ]

        for d in devices:
            d["rssi"] = random.randint(-70, -30) if d["is_online"] else None
            d["battery_level"] = random.randint(60, 100) if d["device_type"] == "mesh_node" else None
            d["firmware_version"] = "1.0.0-sim"

        online = [d for d in devices if d["is_online"]]
        offline = [d for d in devices if not d["is_online"]]

        return {
            "success": True,
            "total_devices": len(devices),
            "online": len(online),
            "offline": len(offline),
            "health_status": "healthy" if len(offline) == 0 else "degraded",
            "devices": devices,
            "simulated": True
        }

    async def get_iot_alerts(
        self,
        hours: int = 24,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Obtener alertas del sistema IoT.

        Args:
            hours: Horas a consultar (default: 24)
            severity: Filtrar por severidad (warning, critical, emergency)
            acknowledged: Filtrar por estado de reconocimiento

        Returns:
            Lista de alertas con detalles
        """
        try:
            url = f"{self.iot_gateway_url}/api/alerts"
            params = {"hours": hours}
            if acknowledged is not None:
                params["acknowledged"] = acknowledged

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        alerts = data.get("alerts", data) if isinstance(data, dict) else data

                        if severity:
                            alerts = [a for a in alerts if a.get("severity") == severity]

                        # Clasificar por severidad
                        by_severity = {
                            "emergency": [],
                            "critical": [],
                            "warning": [],
                            "info": []
                        }

                        for alert in alerts:
                            sev = alert.get("severity", "info")
                            if sev in by_severity:
                                by_severity[sev].append(alert)

                        active_count = len([a for a in alerts if not a.get("acknowledged", False)])

                        return {
                            "success": True,
                            "total_alerts": len(alerts),
                            "active_alerts": active_count,
                            "by_severity": {k: len(v) for k, v in by_severity.items()},
                            "alerts": alerts[:20],  # Ultimas 20
                            "requires_attention": active_count > 0
                        }

            # Fallback simulado
            return self._get_simulated_alerts(severity)

        except Exception as e:
            logger.error(f"[AdminTools] Error en get_iot_alerts: {e}")
            return self._get_simulated_alerts(severity)

    def _get_simulated_alerts(self, severity: Optional[str]) -> Dict[str, Any]:
        """Alertas simuladas"""
        import random

        alerts = []

        # Simular algunas alertas ocasionalmente
        if random.random() < 0.3:
            alerts.append({
                "alert_id": "alert-001",
                "device_id": "mesh-node-001",
                "severity": "warning",
                "message": "Temperatura alta en cocina",
                "value": round(random.uniform(32, 36), 1),
                "threshold": 32.0,
                "location": "cocina",
                "acknowledged": False,
                "timestamp": datetime.now().isoformat()
            })

        if random.random() < 0.15:
            alerts.append({
                "alert_id": "alert-002",
                "device_id": "mesh-node-003",
                "severity": "warning",
                "message": "CO2 elevado en comedor",
                "value": random.randint(900, 1200),
                "threshold": 800,
                "location": "comedor",
                "acknowledged": False,
                "timestamp": datetime.now().isoformat()
            })

        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]

        by_severity = {"emergency": 0, "critical": 0, "warning": len(alerts), "info": 0}

        return {
            "success": True,
            "total_alerts": len(alerts),
            "active_alerts": len([a for a in alerts if not a.get("acknowledged", False)]),
            "by_severity": by_severity,
            "alerts": alerts,
            "requires_attention": len(alerts) > 0,
            "simulated": True
        }

    async def analyze_environment(
        self,
        location: Optional[str] = None,
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Analizar condiciones ambientales del restaurante con recomendaciones.

        Esta es la herramienta principal para que el admin pregunte sobre
        el ambiente, temperatura, calidad del aire, etc.

        Args:
            location: Ubicacion especifica a analizar (opcional)
            include_recommendations: Incluir recomendaciones de mejora

        Returns:
            Analisis completo con metricas y recomendaciones
        """
        try:
            # Obtener datos de sensores
            sensors = await self.get_sensor_readings(location=location)
            devices = await self.get_device_status()
            alerts = await self.get_iot_alerts(hours=4, acknowledged=False)

            sensor_data = sensors.get("by_sensor_type", {})

            # Analizar cada tipo de sensor
            analysis = {
                "temperature": self._analyze_temperature(sensor_data.get("temperature", [])),
                "humidity": self._analyze_humidity(sensor_data.get("humidity", [])),
                "air_quality": self._analyze_air_quality(sensor_data.get("co2", []), sensor_data.get("smoke", []))
            }

            # Estado general
            statuses = [a["status"] for a in analysis.values()]
            if "critical" in statuses:
                overall_status = "critical"
                overall_emoji = "🔴"
            elif "warning" in statuses:
                overall_status = "warning"
                overall_emoji = "🟡"
            else:
                overall_status = "optimal"
                overall_emoji = "🟢"

            # Generar recomendaciones
            recommendations = []
            if include_recommendations:
                recommendations = self._generate_environment_recommendations(analysis, alerts)

            return {
                "success": True,
                "location": location or "todas las areas",
                "overall_status": overall_status,
                "overall_emoji": overall_emoji,
                "analysis": analysis,
                "active_alerts": alerts.get("active_alerts", 0),
                "devices_online": f"{devices.get('online', 0)}/{devices.get('total_devices', 0)}",
                "recommendations": recommendations,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en analyze_environment: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_temperature(self, readings: List[Dict]) -> Dict[str, Any]:
        """Analizar lecturas de temperatura"""
        if not readings:
            return {"status": "unknown", "message": "Sin datos de temperatura"}

        values = [r.get("value", 0) for r in readings]
        avg = sum(values) / len(values)
        max_val = max(values)

        if max_val > 35:
            status = "critical"
            message = f"Temperatura critica detectada: {max_val}°C"
        elif max_val > 30:
            status = "warning"
            message = f"Temperatura alta: {max_val}°C"
        elif avg < 18:
            status = "warning"
            message = f"Temperatura baja: {avg:.1f}°C promedio"
        else:
            status = "optimal"
            message = f"Temperatura optima: {avg:.1f}°C promedio"

        return {
            "status": status,
            "message": message,
            "current_avg": round(avg, 1),
            "max": round(max_val, 1),
            "readings": len(readings),
            "optimal_range": "20-28°C"
        }

    def _analyze_humidity(self, readings: List[Dict]) -> Dict[str, Any]:
        """Analizar lecturas de humedad"""
        if not readings:
            return {"status": "unknown", "message": "Sin datos de humedad"}

        values = [r.get("value", 0) for r in readings]
        avg = sum(values) / len(values)

        if avg > 75:
            status = "warning"
            message = f"Humedad alta: {avg:.0f}%"
        elif avg < 35:
            status = "warning"
            message = f"Humedad baja: {avg:.0f}%"
        else:
            status = "optimal"
            message = f"Humedad optima: {avg:.0f}%"

        return {
            "status": status,
            "message": message,
            "current_avg": round(avg, 0),
            "optimal_range": "40-60%"
        }

    def _analyze_air_quality(self, co2_readings: List[Dict], smoke_readings: List[Dict]) -> Dict[str, Any]:
        """Analizar calidad del aire"""
        status = "optimal"
        issues = []

        if co2_readings:
            co2_values = [r.get("value", 0) for r in co2_readings]
            max_co2 = max(co2_values)
            if max_co2 > 1000:
                status = "critical"
                issues.append(f"CO2 muy alto: {max_co2} ppm")
            elif max_co2 > 800:
                status = "warning"
                issues.append(f"CO2 elevado: {max_co2} ppm")

        if smoke_readings:
            smoke_values = [r.get("value", 0) for r in smoke_readings]
            max_smoke = max(smoke_values)
            if max_smoke > 50:
                status = "critical"
                issues.append(f"Humo detectado: {max_smoke} ppm")
            elif max_smoke > 25:
                if status != "critical":
                    status = "warning"
                issues.append(f"Humo leve: {max_smoke} ppm")

        if not issues:
            message = "Calidad del aire optima"
        else:
            message = "; ".join(issues)

        return {
            "status": status,
            "message": message,
            "issues": issues,
            "optimal_co2": "< 800 ppm"
        }

    def _generate_environment_recommendations(
        self,
        analysis: Dict[str, Any],
        alerts: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generar recomendaciones basadas en analisis ambiental"""
        recommendations = []

        temp = analysis.get("temperature", {})
        if temp.get("status") == "critical":
            recommendations.append({
                "priority": "alta",
                "area": "temperatura",
                "action": "Activar ventilacion de emergencia y revisar aire acondicionado",
                "reason": temp.get("message")
            })
        elif temp.get("status") == "warning":
            recommendations.append({
                "priority": "media",
                "area": "temperatura",
                "action": "Ajustar termostato o incrementar ventilacion",
                "reason": temp.get("message")
            })

        humidity = analysis.get("humidity", {})
        if humidity.get("status") == "warning":
            if "alta" in humidity.get("message", "").lower():
                recommendations.append({
                    "priority": "media",
                    "area": "humedad",
                    "action": "Activar deshumidificador o mejorar ventilacion",
                    "reason": humidity.get("message")
                })
            else:
                recommendations.append({
                    "priority": "baja",
                    "area": "humedad",
                    "action": "Considerar uso de humidificador",
                    "reason": humidity.get("message")
                })

        air = analysis.get("air_quality", {})
        if air.get("status") in ["critical", "warning"]:
            recommendations.append({
                "priority": "alta" if air.get("status") == "critical" else "media",
                "area": "calidad_aire",
                "action": "Incrementar ventilacion, revisar extractor de cocina",
                "reason": air.get("message")
            })

        if alerts.get("active_alerts", 0) > 0:
            recommendations.append({
                "priority": "alta",
                "area": "alertas",
                "action": f"Revisar {alerts.get('active_alerts')} alerta(s) activa(s)",
                "reason": "Alertas sin atender del sistema IoT"
            })

        if not recommendations:
            recommendations.append({
                "priority": "info",
                "area": "general",
                "action": "Mantener condiciones actuales",
                "reason": "Todos los parametros dentro de rangos optimos"
            })

        return recommendations

    async def acknowledge_alert(self, alert_id: str) -> Dict[str, Any]:
        """
        Reconocer/atender una alerta del sistema IoT.

        Args:
            alert_id: ID de la alerta a reconocer

        Returns:
            Resultado de la operacion
        """
        try:
            url = f"{self.iot_gateway_url}/api/alerts/{alert_id}/acknowledge"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": f"Alerta {alert_id} reconocida exitosamente",
                            "alert_id": alert_id
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"No se pudo reconocer la alerta: {response.status}"
                        }

        except Exception as e:
            logger.error(f"[AdminTools] Error en acknowledge_alert: {e}")
            return {
                "success": True,
                "message": f"Alerta {alert_id} reconocida (simulado)",
                "simulated": True
            }

    # ==========================================================================
    # WHATSAPP BROADCAST
    # ==========================================================================

    async def send_whatsapp_broadcast(
        self,
        audience_filter: Dict,
        promotion_id: Optional[str] = None,
        custom_message: Optional[str] = None,
        personalize: bool = True
    ) -> Dict[str, Any]:
        """
        Envía promoción o mensaje broadcast a clientes por WhatsApp.

        Args:
            audience_filter: Filtro de audiencia (segmento de clientes)
            promotion_id: ID de la promoción a enviar (opcional)
            custom_message: Mensaje personalizado (opcional)
            personalize: Si debe personalizar el mensaje por cliente

        Returns:
            Resultado del broadcast con estadísticas
        """
        try:
            from ...whatsapp import get_broadcast_manager, get_customer_segmenter

            broadcast_mgr = get_broadcast_manager()

            # Obtener preview de cuántos clientes serán afectados
            segmenter = get_customer_segmenter()
            customer_count = await segmenter.get_segment_count(audience_filter)

            logger.info(
                f"[AdminTools] Broadcast solicitado: "
                f"promo_id={promotion_id}, segment={audience_filter.get('segment')}, "
                f"clientes={customer_count}"
            )

            if customer_count == 0:
                return {
                    "success": False,
                    "error": "No hay clientes que cumplan con los criterios seleccionados",
                    "customer_count": 0
                }

            # Enviar broadcast
            if promotion_id:
                result = await broadcast_mgr.send_promotion(
                    promotion_id=promotion_id,
                    audience_filter=audience_filter,
                    custom_message=custom_message,
                    personalize=personalize
                )
            else:
                if not custom_message:
                    return {
                        "success": False,
                        "error": "Debes proporcionar promotion_id o custom_message"
                    }

                result = await broadcast_mgr.send_custom_broadcast(
                    message=custom_message,
                    audience_filter=audience_filter,
                    buttons=[
                        {"id": "order_now", "title": "Ordenar ahora"},
                        {"id": "view_menu", "title": "Ver menú"}
                    ]
                )

            # Formatear respuesta para el admin
            segment_desc = segmenter.get_segment_description(audience_filter.get('segment', 'custom'))

            return {
                "success": True,
                "message": f"✅ Broadcast enviado exitosamente",
                "campaign_id": result.campaign_id,
                "statistics": {
                    "total_sent": result.total_sent,
                    "successful": result.successful,
                    "failed": result.failed,
                    "success_rate": f"{(result.successful / result.total_sent * 100) if result.total_sent > 0 else 0:.1f}%"
                },
                "segment": segment_desc,
                "failed_numbers": result.failed_numbers if result.failed > 0 else [],
                "next_steps": "Puedes ver las estadísticas en tiempo real en el dashboard de WhatsApp"
            }

        except Exception as e:
            logger.error(f"[AdminTools] Error en send_whatsapp_broadcast: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error enviando broadcast: {str(e)}"
            }

    # ==========================================================================
    # EJECUTOR PRINCIPAL
    # ==========================================================================

    async def execute(self, tool_name: str, parameters: Dict) -> Dict[str, Any]:
        """
        Ejecutar una herramienta por nombre.

        Args:
            tool_name: Nombre de la herramienta
            parameters: Parametros de la herramienta

        Returns:
            Resultado de la ejecucion
        """
        tool_map = {
            # Herramientas originales
            "get_sales_report": self.get_sales_report,
            "get_top_products": self.get_top_products,
            "get_orders_count": self.get_orders_count,
            "get_hourly_sales": self.get_hourly_sales,
            "get_average_ticket": self.get_average_ticket,
            "generate_daily_report": self.generate_daily_report,
            "create_promotion": self.create_promotion,
            "toggle_promotion": self.toggle_promotion,
            "list_promotions": self.list_promotions,
            "create_product": self.create_product,
            "toggle_product": self.toggle_product,
            "update_product_price": self.update_product_price,
            "get_unavailable_products": self.get_unavailable_products,
            # Herramientas de analisis financiero
            "analyze_food_cost": self.analyze_food_cost,
            "analyze_product_performance": self.analyze_product_performance,
            "analyze_sales_trend": self.analyze_sales_trend,
            "get_margin_analysis": self.get_margin_analysis,
            "generate_proactive_insights": self.generate_proactive_insights,
            "compare_periods": self.compare_periods,
            # Herramientas IoT - Sensores ESP32 MESH/ROUTER
            "get_sensor_readings": self.get_sensor_readings,
            "get_sensor_history": self.get_sensor_history,
            "get_device_status": self.get_device_status,
            "get_iot_alerts": self.get_iot_alerts,
            "analyze_environment": self.analyze_environment,
            "acknowledge_alert": self.acknowledge_alert,
            # WhatsApp Broadcast
            "send_whatsapp_broadcast": self.send_whatsapp_broadcast
        }

        if tool_name not in tool_map:
            return {
                "success": False,
                "error": f"Herramienta '{tool_name}' no encontrada"
            }

        try:
            result = await tool_map[tool_name](**parameters)
            logger.info(f"[AdminTools] Ejecutado: {tool_name} -> success={result.get('success')}")
            return result
        except Exception as e:
            logger.error(f"[AdminTools] Error ejecutando {tool_name}: {e}")
            return {"success": False, "error": str(e)}


# ==============================================================================
# SINGLETON
# ==============================================================================

_admin_tools: Optional[AdminTools] = None


def get_admin_tools() -> AdminTools:
    """Obtener instancia singleton de AdminTools"""
    global _admin_tools
    if _admin_tools is None:
        _admin_tools = AdminTools()
    return _admin_tools
