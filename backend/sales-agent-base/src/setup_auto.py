#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Setup Automático del Proyecto

Este módulo se ejecuta automáticamente al iniciar el proyecto y:
1. Verifica que todo esté configurado
2. Crea directorios necesarios
3. Configura la automatización (primera vez)
4. Valida dependencias

Se ejecuta de forma transparente sin intervención del usuario.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from datetime import datetime


class AutoSetup:
    """Configuración automática del proyecto"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.setup_flag = self.base_dir / '.setup_completed'
        self.is_windows = platform.system() == 'Windows'
        self.first_run = not self.setup_flag.exists()

    def run(self, silent=False):
        """
        Ejecuta el setup automático

        Args:
            silent: Si True, no muestra mensajes (solo errores)

        Returns:
            bool: True si todo OK
        """
        if not silent:
            if self.first_run:
                print("\n" + "=" * 70)
                print("  🔧 PRIMERA EJECUCIÓN - Configurando proyecto...")
                print("=" * 70 + "\n")
            else:
                print("✅ Proyecto ya configurado")

        # 1. Crear directorios
        if not self._create_directories():
            return False

        # 2. Verificar Python y dependencias (solo avisos)
        self._check_dependencies(silent)

        # 3. Configurar automatización (solo primera vez)
        if self.first_run:
            if not silent:
                print("\n📅 Configurando automatización semanal...")

            self._configure_automation(silent)

            # Marcar como completado
            self._mark_setup_complete()

            if not silent:
                print("\n" + "=" * 70)
                print("  ✅ SETUP COMPLETADO")
                print("=" * 70)
                print("\nEl proyecto está listo. Iniciando...\n")

        return True

    def _create_directories(self):
        """Crea directorios necesarios"""
        directories = [
            'optimization_logs',
            'conversation_archive',
            'backups',
            'logs',
            'temp'
        ]

        try:
            for dir_name in directories:
                dir_path = self.base_dir / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)

            return True

        except Exception as e:
            print(f"⚠️  Error creando directorios: {e}")
            return False

    def _check_dependencies(self, silent=False):
        """Verifica dependencias (solo avisos, no falla)"""
        try:
            # Verificar módulo principal
            import src.learning.fsm_optimizer  # noqa
            if not silent:
                print("✅ FSM Optimizer disponible")

        except ImportError as e:
            if not silent:
                print(f"⚠️  Advertencia: {e}")
                print("   Algunas funcionalidades pueden no estar disponibles")

        # Verificar multi-tenant
        try:
            from src.core.tenant_manager import get_tenant_manager
            tenant_manager = get_tenant_manager()
            tenants = tenant_manager.list_tenants()
            if not silent:
                print(f"✅ Multi-tenant: {len(tenants)} tenant(s) configurado(s)")

        except Exception as e:
            if not silent:
                print(f"⚠️  Multi-tenant: {e}")

    def _configure_automation(self, silent=False):
        """Configura la automatización semanal"""
        if not self.is_windows:
            if not silent:
                print("ℹ️  Sistema no-Windows detectado")
                print("   Configuración de cron manual requerida")
            return

        try:
            # Verificar si la tarea ya existe
            result = subprocess.run(
                ['schtasks', '/query', '/tn', 'FSM_Optimizer_Semanal'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                if not silent:
                    print("✅ Tarea programada ya existe")
                return

            # Intentar crear tarea
            script_path = self.base_dir / 'run_fsm_optimization.bat'

            if not script_path.exists():
                if not silent:
                    print("⚠️  Script de optimización no encontrado")
                return

            # Crear tarea programada
            result = subprocess.run([
                'schtasks', '/create',
                '/tn', 'FSM_Optimizer_Semanal',
                '/tr', f'"{script_path}"',
                '/sc', 'weekly',
                '/d', 'SUN',
                '/st', '03:00',
                '/ru', 'SYSTEM',
                '/f'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                if not silent:
                    print("✅ Tarea programada creada exitosamente")
                    print("   - Frecuencia: Domingos 3:00 AM")
                    print("   - Nombre: FSM_Optimizer_Semanal")
            else:
                if not silent:
                    print("⚠️  No se pudo crear tarea automáticamente")
                    print("   - Requiere permisos de administrador")
                    print("   - Ejecuta: configurar_automatizacion.bat")

        except Exception as e:
            if not silent:
                print(f"⚠️  Error configurando automatización: {e}")

    def _mark_setup_complete(self):
        """Marca el setup como completado"""
        try:
            with open(self.setup_flag, 'w', encoding='utf-8') as f:
                f.write(f"Setup completado: {datetime.now()}\n")
                f.write(f"Python: {sys.version}\n")
                f.write(f"Platform: {platform.platform()}\n")

        except Exception as e:
            print(f"⚠️  Error guardando flag de setup: {e}")

    def check_automation_status(self):
        """
        Verifica el estado de la automatización

        Returns:
            dict: Estado de la automatización
        """
        status = {
            'configured': False,
            'next_run': None,
            'task_name': 'FSM_Optimizer_Semanal'
        }

        if not self.is_windows:
            return status

        try:
            result = subprocess.run(
                ['schtasks', '/query', '/tn', status['task_name'], '/fo', 'list'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                status['configured'] = True

                # Extraer próxima ejecución
                for line in result.stdout.split('\n'):
                    if 'próxima' in line.lower() or 'next run' in line.lower():
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            status['next_run'] = parts[1].strip()
                        break

        except Exception:
            pass

        return status


# Función de conveniencia
def setup_proyecto(silent=False):
    """
    Ejecuta el setup automático del proyecto

    Args:
        silent: Si True, ejecuta en modo silencioso

    Returns:
        bool: True si el setup fue exitoso
    """
    setup = AutoSetup()
    return setup.run(silent=silent)


def verificar_automatizacion():
    """Verifica y muestra el estado de la automatización"""
    setup = AutoSetup()
    status = setup.check_automation_status()

    print("\n" + "=" * 70)
    print("  📅 ESTADO DE AUTOMATIZACIÓN")
    print("=" * 70)

    if status['configured']:
        print("\n✅ Automatización CONFIGURADA")
        print(f"   Tarea: {status['task_name']}")

        if status['next_run']:
            print(f"   Próxima ejecución: {status['next_run']}")
        else:
            print("   Próxima ejecución: Ver Programador de Tareas")

        print("\n   El FSM Optimizer se ejecutará automáticamente")
        print("   cada domingo a las 3:00 AM.")

    else:
        print("\n⚠️  Automatización NO CONFIGURADA")
        print("\n   Para configurar:")

        if setup.is_windows:
            print("   1. Ejecuta como Administrador: configurar_automatizacion.bat")
            print("   2. O configura manualmente en Programador de Tareas")
        else:
            print("   1. Ejecuta: crontab -e")
            print("   2. Agrega: 0 3 * * 0 /path/to/run_fsm_optimization.sh")

    print("\n" + "=" * 70 + "\n")

    return status


if __name__ == "__main__":
    # Si se ejecuta directamente, mostrar estado
    if len(sys.argv) > 1 and sys.argv[1] == '--status':
        verificar_automatizacion()
    else:
        setup_proyecto(silent=False)
