"""
================================================================================
DEMO HANDLER - Gestión del Flujo de Demo Interactiva
================================================================================
Maneja la interacción de prospectos con las demos multi-industria
================================================================================
"""

from typing import Dict, Any, Optional, Tuple
import logging
import json
import os
from datetime import datetime

from .demo_config import (
    DemoIndustry, DEMO_CATALOGS, DEMO_INITIAL_POINTS,
    get_demo_catalog, get_industry_menu, get_demo_info_message
)
from .loyalty_handler import get_loyalty_handler
from .loyalty_models import EarnPointsRequest

logger = logging.getLogger(__name__)


class DemoProspect:
    """Datos de un prospecto en la demo"""
    def __init__(self, phone: str):
        self.phone = phone
        self.current_industry: Optional[DemoIndustry] = None
        self.industries_explored: list = []
        self.initial_points_granted: bool = False
        self.completed_checkout: bool = False
        self.requested_info: bool = False
        self.created_at: datetime = datetime.utcnow()
        self.last_interaction: datetime = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone": self.phone,
            "current_industry": self.current_industry.value if self.current_industry else None,
            "industries_explored": [i.value for i in self.industries_explored],
            "initial_points_granted": self.initial_points_granted,
            "completed_checkout": self.completed_checkout,
            "requested_info": self.requested_info,
            "created_at": self.created_at.isoformat(),
            "last_interaction": self.last_interaction.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DemoProspect':
        prospect = cls(data["phone"])
        prospect.current_industry = DemoIndustry(data["current_industry"]) if data.get("current_industry") else None
        prospect.industries_explored = [DemoIndustry(i) for i in data.get("industries_explored", [])]
        prospect.initial_points_granted = data.get("initial_points_granted", False)
        prospect.completed_checkout = data.get("completed_checkout", False)
        prospect.requested_info = data.get("requested_info", False)
        if data.get("created_at"):
            prospect.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_interaction"):
            prospect.last_interaction = datetime.fromisoformat(data["last_interaction"])
        return prospect


class DemoHandler:
    """
    Manejador del flujo de demo interactiva.

    Funcionalidades:
    - Detectar prospectos nuevos
    - Asignar puntos iniciales automáticamente
    - Gestionar selección de industria
    - Mantener contexto de exploración
    - Registrar analytics
    """

    def __init__(self, data_dir: str = "data/demo"):
        self.data_dir = data_dir
        self._ensure_data_directory()

        # Cache de prospectos
        self._prospects: Dict[str, DemoProspect] = {}

        # Loyalty handler para otorgar puntos
        self.loyalty_handler = get_loyalty_handler()

        # Cargar prospectos existentes
        self._load_prospects()

    def _ensure_data_directory(self):
        """Crear directorio de datos si no existe"""
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_prospects(self):
        """Cargar prospectos desde archivo"""
        try:
            filepath = f"{self.data_dir}/prospects.json"
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for phone, prospect_data in data.items():
                        self._prospects[phone] = DemoProspect.from_dict(prospect_data)
                logger.info(f"[Demo] Cargados {len(self._prospects)} prospectos")
        except Exception as e:
            logger.error(f"[Demo] Error cargando prospectos: {e}")

    def _save_prospect(self, prospect: DemoProspect):
        """Guardar prospecto en archivo"""
        try:
            self._prospects[prospect.phone] = prospect

            filepath = f"{self.data_dir}/prospects.json"
            data = {phone: p.to_dict() for phone, p in self._prospects.items()}

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[Demo] Error guardando prospecto: {e}")

    async def handle_new_prospect(self, phone: str) -> Tuple[DemoProspect, str]:
        """
        Procesar prospecto nuevo.

        Returns:
            (prospect, welcome_message)
        """
        if phone in self._prospects:
            prospect = self._prospects[phone]
            prospect.last_interaction = datetime.utcnow()
            self._save_prospect(prospect)

            # Si ya tiene industria, devolver mensaje de esa industria
            if prospect.current_industry:
                catalog = get_demo_catalog(prospect.current_industry)
                return prospect, catalog["welcome_message"]

            # Si no tiene industria, mostrar menú
            return prospect, self._get_welcome_message()

        # Crear nuevo prospecto
        prospect = DemoProspect(phone)
        self._save_prospect(prospect)

        logger.info(f"[Demo] Nuevo prospecto: {phone}")

        return prospect, self._get_welcome_message()

    def _get_welcome_message(self) -> str:
        """Mensaje de bienvenida inicial"""
        return f"""👋 ¡Bienvenido a la DEMO INTERACTIVA!

Soy un asistente con IA. Aquí puedes PROBAR EN VIVO
cómo funciona nuestro sistema de ventas por WhatsApp.

✨ En esta demo:
✅ Exploras negocios reales (restaurante, tienda, etc)
✅ Navegas catálogos web completos
✅ Pruebas el checkout con puntos de fidelidad
✅ Recibes confirmaciones automáticas

🎁 Te daré {DEMO_INITIAL_POINTS} puntos de regalo para que
   pruebes cómo funciona el sistema de fidelidad.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{get_industry_menu()}"""

    async def select_industry(
        self,
        phone: str,
        selection: str
    ) -> Tuple[bool, str, Optional[DemoIndustry]]:
        """
        Procesar selección de industria.

        Args:
            phone: Teléfono del prospecto
            selection: Número de opción seleccionada

        Returns:
            (success, message, industry)
        """
        # Mapear selección a industria
        industry_map = {
            "1": DemoIndustry.RESTAURANT,
            "2": DemoIndustry.RETAIL,
            "3": DemoIndustry.PHARMACY,
            "4": DemoIndustry.GROCERY,
            "5": DemoIndustry.SERVICES,
            "6": DemoIndustry.PETS
        }

        industry = industry_map.get(selection.strip())
        if not industry:
            return False, "Por favor escribe un número del 1 al 6", None

        # Obtener o crear prospecto
        prospect = self._prospects.get(phone)
        if not prospect:
            prospect = DemoProspect(phone)

        # Actualizar industria actual
        old_industry = prospect.current_industry
        prospect.current_industry = industry

        if industry not in prospect.industries_explored:
            prospect.industries_explored.append(industry)

        prospect.last_interaction = datetime.utcnow()
        self._save_prospect(prospect)

        # Otorgar puntos iniciales si es primera vez
        if not prospect.initial_points_granted:
            await self._grant_initial_points(prospect, industry)
            prospect.initial_points_granted = True
            self._save_prospect(prospect)

        # Obtener catálogo y mensaje de bienvenida
        catalog = get_demo_catalog(industry)

        message = f"""🎉 ¡Perfecto! Ahora eres cliente de:

{catalog['icon']} {catalog['name'].upper()}
{catalog['description']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Te voy a mostrar exactamente cómo tus clientes
ordenarían en TU negocio.

Para esta demo, tienes:
✅ {DEMO_INITIAL_POINTS} puntos de fidelidad (para probar el canje)
✅ Catálogo completo de productos
✅ Checkout funcional (sin pagos reales)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{catalog['welcome_message']}"""

        if old_industry and old_industry != industry:
            message = f"""👍 ¡Cambiando de escenario!

Tus puntos actuales quedan guardados por si
quieres regresar a {get_demo_catalog(old_industry)['name']}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{message}"""

        logger.info(f"[Demo] {phone} seleccionó: {industry.value}")

        return True, message, industry

    async def _grant_initial_points(
        self,
        prospect: DemoProspect,
        industry: DemoIndustry
    ):
        """Otorgar puntos iniciales al prospecto"""
        try:
            # Crear un "pedido ficticio" para otorgar puntos
            request = EarnPointsRequest(
                customer_phone=prospect.phone,
                restaurant_id=industry.value,
                order_id=f"DEMO-INITIAL-{prospect.phone[-4:]}",
                order_total=DEMO_INITIAL_POINTS * 10,  # Para que genere exactamente los puntos que queremos
                customer_name="Demo Prospecto"
            )

            result = await self.loyalty_handler.earn_points(request)

            logger.info(
                f"[Demo] Puntos iniciales otorgados a {prospect.phone}: "
                f"{result.get('points_earned', 0)} pts"
            )
        except Exception as e:
            logger.error(f"[Demo] Error otorgando puntos iniciales: {e}")

    def handle_command(
        self,
        phone: str,
        message: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Detectar y manejar comandos especiales de la demo.

        Args:
            phone: Teléfono del prospecto
            message: Mensaje recibido

        Returns:
            (is_command, response_message)
        """
        message_lower = message.lower().strip()

        # Comando: cambiar de industria
        if message_lower in ["cambiar", "change", "otro", "volver"]:
            prospect = self._prospects.get(phone)
            if prospect:
                prospect.current_industry = None
                self._save_prospect(prospect)

            return True, f"""👍 ¡Perfecto! Vamos a cambiar de escenario.

{get_industry_menu()}"""

        # Comando: información y precios
        if message_lower in ["info", "precios", "planes", "precio", "contratar"]:
            prospect = self._prospects.get(phone)
            if prospect:
                prospect.requested_info = True
                self._save_prospect(prospect)

            return True, get_demo_info_message()

        # Comando: ayuda
        if message_lower in ["ayuda", "help", "?", "menu"]:
            return True, f"""🆘 AYUDA - COMANDOS DISPONIBLES

Puedes escribir:

• *cambiar* - Explorar otro tipo de negocio
• *info* - Ver planes y precios
• *ayuda* - Ver este menú de ayuda

O simplemente interactúa como lo harían
tus clientes: pide productos, consulta
puntos, etc.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

¿Qué quieres hacer?"""

        return False, None

    def get_prospect(self, phone: str) -> Optional[DemoProspect]:
        """Obtener datos del prospecto"""
        return self._prospects.get(phone)

    def mark_checkout_completed(self, phone: str):
        """Marcar que el prospecto completó un checkout"""
        prospect = self._prospects.get(phone)
        if prospect:
            prospect.completed_checkout = True
            prospect.last_interaction = datetime.utcnow()
            self._save_prospect(prospect)
            logger.info(f"[Demo] {phone} completó checkout")

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Obtener resumen de analytics de la demo"""
        total_prospects = len(self._prospects)
        completed_checkouts = sum(1 for p in self._prospects.values() if p.completed_checkout)
        requested_info = sum(1 for p in self._prospects.values() if p.requested_info)

        # Contar por industria
        industry_counts = {}
        for prospect in self._prospects.values():
            for industry in prospect.industries_explored:
                industry_counts[industry.value] = industry_counts.get(industry.value, 0) + 1

        conversion_rate = (requested_info / total_prospects * 100) if total_prospects > 0 else 0

        return {
            "total_prospects": total_prospects,
            "completed_checkouts": completed_checkouts,
            "requested_info": requested_info,
            "conversion_rate": round(conversion_rate, 2),
            "industry_popularity": industry_counts,
            "checkout_rate": round((completed_checkouts / total_prospects * 100), 2) if total_prospects > 0 else 0
        }


# ==============================================================================
# SINGLETON INSTANCE
# ==============================================================================

_demo_handler_instance = None


def get_demo_handler() -> DemoHandler:
    """Obtener instancia singleton del demo handler"""
    global _demo_handler_instance
    if _demo_handler_instance is None:
        _demo_handler_instance = DemoHandler()
    return _demo_handler_instance
