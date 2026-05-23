#!/usr/bin/env python3
"""
================================================================================
TEST DE UMBRALES DE DERIVACIÓN
================================================================================
Script para probar y verificar cuántos mensajes se generan antes de derivar
a web en diferentes escenarios.
================================================================================
"""

import sys
import os

# Agregar path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'whatsapp-gateway', 'src'))

from intent_detector import IntentDetector, ConversationIntent
from hybrid_session import DerivarReason


class SimuladorDerivacion:
    """Simula conversaciones para identificar cuándo se deriva a web"""

    def __init__(self):
        self.detector = IntentDetector()
        self.min_messages = 3  # MIN_MESSAGES_DERIVAR default

    def simular_conversacion(self, nombre_escenario: str, mensajes: list, notas: str = ""):
        """
        Simula una conversación y detecta en qué mensaje se deriva a web.

        Args:
            nombre_escenario: Nombre del escenario
            mensajes: Lista de mensajes del usuario
            notas: Notas adicionales sobre el escenario
        """
        print("\n" + "=" * 80)
        print(f"ESCENARIO: {nombre_escenario}")
        print("=" * 80)
        if notas:
            print(f"📝 {notas}")
            print("-" * 80)

        cart_size = 0
        derivado = False
        mensaje_derivacion = None
        razon_derivacion = None

        for idx, mensaje in enumerate(mensajes, start=1):
            # Detectar intent
            intent, confidence = self.detector.detect_intent(mensaje)

            # Simular agregar al carrito si es order intent
            if intent in [ConversationIntent.QUICK_ORDER, ConversationIntent.COMPLEX_ORDER]:
                # Contar items mencionados (simplificado)
                if "y" in mensaje.lower():
                    cart_size += 2
                else:
                    cart_size += 1

            # Verificar si debe derivar
            should_redirect, reason = self.detector.should_redirect_to_web(
                intent=intent,
                message_count=idx,
                cart_size=cart_size,
                confidence=confidence,
                user_message=mensaje
            )

            # Aplicar regla de mínimo de mensajes
            if should_redirect and idx < self.min_messages:
                should_redirect = False
                status = f"⏸️  [POSPUESTO - Mínimo {self.min_messages} mensajes]"
            elif should_redirect:
                status = f"🔴 [DERIVA A WEB - {reason.value if reason else 'unknown'}]"
                derivado = True
                mensaje_derivacion = idx
                razon_derivacion = reason
            else:
                status = "✅ [En WhatsApp]"

            print(f"\nMensaje {idx}: \"{mensaje}\"")
            print(f"  Intent: {intent} ({confidence:.2f})")
            print(f"  Cart: {cart_size} items")
            print(f"  Status: {status}")

            if derivado:
                break

        print("\n" + "-" * 80)
        if derivado:
            print(f"✅ RESULTADO: Derivó a web en mensaje #{mensaje_derivacion}")
            print(f"   Razón: {razon_derivacion.value if razon_derivacion else 'unknown'}")
            print(f"   Total mensajes antes de derivar: {mensaje_derivacion}")
        else:
            print(f"✅ RESULTADO: Conversación completa en WhatsApp")
            print(f"   Total mensajes: {len(mensajes)}")
            print(f"   Cart final: {cart_size} items")
        print("=" * 80)


def main():
    """Ejecutar simulaciones de todos los escenarios"""
    sim = SimuladorDerivacion()

    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "SIMULADOR DE UMBRALES DE DERIVACIÓN" + " " * 23 + "║")
    print("║" + " " * 78 + "║")
    print("║" + "  Verifica cuántos mensajes se generan antes de derivar a web" + " " * 16 + "║")
    print("╚" + "=" * 78 + "╝")

    # =========================================================================
    # ESCENARIO 1: Usuario Directo (Quick Order)
    # =========================================================================
    sim.simular_conversacion(
        nombre_escenario="Usuario Directo - Quick Order",
        mensajes=[
            "Hola",
            "Dame 3 tacos al pastor",
            "Y una coca cola",
            "Cuánto es?",
            "Confirmar pedido"
        ],
        notas="Usuario sabe exactamente qué quiere. Debería completarse en WhatsApp."
    )

    # =========================================================================
    # ESCENARIO 2: Usuario Exploratorio (Browsing Largo)
    # =========================================================================
    sim.simular_conversacion(
        nombre_escenario="Usuario Exploratorio - Conversación Larga",
        mensajes=[
            "Hola",
            "Qué tienen?",
            "Qué tipos de tacos?",
            "Y quesadillas?",
            "Cuánto cuestan los tacos?",
            "Y las hamburguesas?",
            "Qué trae la hamburguesa Deluxe?",
            "Tienen fotos?",
            "Hay promociones?",
            "Qué es lo más popular?"
        ],
        notas="Usuario explorando sin decidir. Debería derivar en mensaje 8 (CONVERSATION_TOO_LONG)."
    )

    # =========================================================================
    # ESCENARIO 3: Solicitud Explícita de Menú
    # =========================================================================
    sim.simular_conversacion(
        nombre_escenario="Solicitud Explícita - Ver Menú Completo",
        mensajes=[
            "Hola",
            "Qué tienen de tacos?",
            "Quiero ver el menú completo con fotos"
        ],
        notas="Usuario pide explícitamente ver menú. Debería derivar en mensaje 3 (USER_REQUESTED)."
    )

    # =========================================================================
    # ESCENARIO 4: Carrito Grande
    # =========================================================================
    sim.simular_conversacion(
        nombre_escenario="Carrito Grande - 5+ Items",
        mensajes=[
            "Hola",
            "Dame 2 tacos",
            "Y 2 hamburguesas",
            "Y 2 refrescos",
            "Y también papas",
            "Agregar una orden de nachos"
        ],
        notas="Usuario va agregando items. Debería derivar cuando cart_size >= 5."
    )

    # =========================================================================
    # ESCENARIO 5: Customización Compleja
    # =========================================================================
    sim.simular_conversacion(
        nombre_escenario="Customización Compleja - Múltiples Sin/Con",
        mensajes=[
            "Hola",
            "Qué hamburguesas tienen?",
            "Dame una hamburguesa sin cebolla, sin tomate, con extra queso, sin pepinillos y con papas"
        ],
        notas="Pedido con muchas personalizaciones. Debería derivar en mensaje 3 (CUSTOMIZATION_NEEDED)."
    )

    # =========================================================================
    # ESCENARIO 6: Usuario Indeciso (Recomendaciones)
    # =========================================================================
    sim.simular_conversacion(
        nombre_escenario="Usuario Indeciso - Pide Recomendaciones",
        mensajes=[
            "Hola",
            "No sé qué pedir",
            "Qué me recomiendas?",
            "Está bueno el pozole?",
            "Y las enchiladas?",
            "Dame la recomendación del chef"
        ],
        notas="Usuario indeciso pidiendo ayuda. Debería mantenerse en WhatsApp (mesero ayuda)."
    )

    # =========================================================================
    # ESCENARIO 7: Consulta Específica (Ingredientes)
    # =========================================================================
    sim.simular_conversacion(
        nombre_escenario="Consulta Específica - Ingredientes",
        mensajes=[
            "Hola",
            "Tienen opciones vegetarianas?",
            "Qué lleva la quesadilla?",
            "Es sin gluten?",
            "Dame 2 quesadillas vegetarianas"
        ],
        notas="Usuario con consultas específicas. Debería resolverse en WhatsApp (CONSULTATION intent)."
    )

    # =========================================================================
    # ESCENARIO 8: Derivación Temprana Bloqueada
    # =========================================================================
    sim.simular_conversacion(
        nombre_escenario="Derivación Temprana Bloqueada - MIN_MESSAGES",
        mensajes=[
            "Hola",
            "Muéstrame el menú completo con fotos",
            "Quiero ver todo"
        ],
        notas="Usuario pide menú en mensaje 2, pero MIN_MESSAGES=3 bloquea. Deriva en mensaje 3."
    )

    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "RESUMEN DE CONFIGURACIÓN" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    print(f"\n📊 MIN_MESSAGES_DERIVAR = {sim.min_messages}")
    print(f"📊 Umbral conversación larga = 8 mensajes (hardcoded)")
    print(f"📊 Umbral carrito grande = 5 items (hardcoded)")
    print(f"📊 Umbral customización = 3 personalizaciones (hardcoded)")
    print("\n")


if __name__ == "__main__":
    main()
