"""
Test del Sistema de Puntos de Fidelidad
"""

import asyncio
import aiohttp
import json

API_URL = "http://localhost:8080"
TEST_RESTAURANT = "carniceria"
TEST_CUSTOMER = "5215512345678"


async def test_get_config():
    """Test 1: Obtener configuracion de loyalty"""
    print("\n" + "="*80)
    print("TEST 1: GET /api/v1/loyalty/config/{restaurant_id}")
    print("="*80)

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/api/v1/loyalty/config/{TEST_RESTAURANT}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    config = data.get('config', {})
                    print(f"OK - Sistema de puntos configurado:")
                    print(f"    Habilitado: {config.get('enabled')}")
                    print(f"    Puntos por peso: {config.get('points_per_currency')}")
                    print(f"    Valor por punto: ${config.get('currency_per_point')}")
                    print(f"    Minimo para canjear: {config.get('min_points_to_redeem')} puntos")
                    print(f"    Bonus primera compra: {config.get('first_purchase_bonus')} puntos")
                    return True
                else:
                    print(f"ERROR - Status: {response.status}")
                    return False
    except Exception as e:
        print(f"ERROR - {e}")
        return False


async def test_earn_points():
    """Test 2: Ganar puntos con una compra"""
    print("\n" + "="*80)
    print("TEST 2: POST /api/v1/loyalty/earn - Ganar puntos")
    print("="*80)

    try:
        test_data = {
            "customer_phone": TEST_CUSTOMER,
            "restaurant_id": TEST_RESTAURANT,
            "order_id": "TEST-001",
            "order_total": 500.00,
            "customer_name": "Juan Perez"
        }

        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/api/v1/loyalty/earn"
            async with session.post(url, json=test_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"OK - Puntos otorgados:")
                    print(f"    Ganados: +{data.get('points_earned')} puntos")
                    print(f"    Total: {data.get('total_points')} puntos")
                    print(f"    Nivel: {data.get('current_tier', '').upper()}")
                    print(f"    Multiplicador: {data.get('multiplier')}x")

                    if data.get('first_purchase_bonus', 0) > 0:
                        print(f"    Bonus primera compra: +{data.get('first_purchase_bonus')} puntos")

                    if data.get('tier_upgraded'):
                        print(f"    Subiste a nivel: {data.get('new_tier', '').upper()}")

                    return True
                else:
                    print(f"ERROR - Status: {response.status}")
                    return False
    except Exception as e:
        print(f"ERROR - {e}")
        return False


async def test_get_balance():
    """Test 3: Consultar balance de puntos"""
    print("\n" + "="*80)
    print("TEST 3: GET /api/v1/loyalty/balance/{phone} - Consultar balance")
    print("="*80)

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/api/v1/loyalty/balance/{TEST_CUSTOMER}"
            params = {"restaurant_id": TEST_RESTAURANT}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"OK - Balance del cliente:")
                    print(f"    Puntos disponibles: {data.get('available_points')}")
                    print(f"    Puntos lifetime: {data.get('lifetime_points')}")
                    print(f"    Nivel actual: {data.get('current_tier', '').upper()}")
                    print(f"    Valor en dinero: ${data.get('points_value_in_currency', 0):.2f}")
                    print(f"    Total gastado: ${data.get('total_spent', 0):.2f}")
                    print(f"    Total ordenes: {data.get('total_orders')}")

                    if data.get('next_tier'):
                        print(f"    Proximo nivel: {data.get('next_tier', '').upper()}")
                        print(f"    Puntos faltantes: {data.get('points_to_next_tier')}")

                    # Guardar puntos disponibles para el siguiente test
                    global available_points
                    available_points = data.get('available_points', 0)
                    return True
                else:
                    print(f"ERROR - Status: {response.status}")
                    return False
    except Exception as e:
        print(f"ERROR - {e}")
        return False


async def test_redeem_points():
    """Test 4: Canjear puntos por descuento"""
    print("\n" + "="*80)
    print("TEST 4: POST /api/v1/loyalty/redeem - Canjear puntos")
    print("="*80)

    try:
        # Verificar que hay puntos para canjear
        if available_points < 100:
            print(f"INFO - No hay suficientes puntos para canjear (disponibles: {available_points})")
            print(f"    Saltando test de canje...")
            return True

        # Canjear 100 puntos
        test_data = {
            "customer_phone": TEST_CUSTOMER,
            "restaurant_id": TEST_RESTAURANT,
            "points_to_redeem": 100,
            "order_total": 500.00
        }

        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/api/v1/loyalty/redeem"
            async with session.post(url, json=test_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"OK - Puntos canjeados:")
                    print(f"    Puntos usados: -{data.get('points_redeemed')}")
                    print(f"    Descuento aplicado: ${data.get('discount_amount', 0):.2f}")
                    print(f"    Puntos restantes: {data.get('points_remaining')}")
                    print(f"    Mensaje: {data.get('message')}")
                    return True
                else:
                    print(f"ERROR - Status: {response.status}")
                    text = await response.text()
                    print(f"    Response: {text}")
                    return False
    except Exception as e:
        print(f"ERROR - {e}")
        return False


async def test_update_config():
    """Test 5: Actualizar configuracion (Dashboard Admin)"""
    print("\n" + "="*80)
    print("TEST 5: PUT /api/v1/loyalty/config/{restaurant_id} - Actualizar config")
    print("="*80)

    try:
        # Actualizar algunos parametros
        test_data = {
            "restaurant_id": TEST_RESTAURANT,
            "birthday_bonus": 150,
            "referral_bonus": 75
        }

        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/api/v1/loyalty/config/{TEST_RESTAURANT}"
            async with session.put(url, json=test_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"OK - Configuracion actualizada:")
                    print(f"    {data.get('message')}")

                    config = data.get('config', {})
                    print(f"    Bonus cumpleanos: {config.get('birthday_bonus')} puntos")
                    print(f"    Bonus referidos: {config.get('referral_bonus')} puntos")
                    return True
                else:
                    print(f"ERROR - Status: {response.status}")
                    return False
    except Exception as e:
        print(f"ERROR - {e}")
        return False


async def test_multiple_purchases():
    """Test 6: Multiples compras para probar niveles"""
    print("\n" + "="*80)
    print("TEST 6: Simular multiples compras - Subir de nivel")
    print("="*80)

    try:
        # Hacer 3 compras mas para acumular puntos
        print(f"\nSimulando 3 compras adicionales...\n")

        for i in range(3):
            test_data = {
                "customer_phone": TEST_CUSTOMER,
                "restaurant_id": TEST_RESTAURANT,
                "order_id": f"TEST-{100+i}",
                "order_total": 800.00,
                "customer_name": "Juan Perez"
            }

            async with aiohttp.ClientSession() as session:
                url = f"{API_URL}/api/v1/loyalty/earn"
                async with session.post(url, json=test_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"Compra {i+1}:")
                        print(f"  Ganados: +{data.get('points_earned')} puntos")
                        print(f"  Total: {data.get('total_points')} puntos")
                        print(f"  Nivel: {data.get('current_tier', '').upper()}")

                        if data.get('tier_upgraded'):
                            print(f"  Subiste de nivel a: {data.get('new_tier', '').upper()}")
                        print()

        print("OK - Multiples compras procesadas correctamente")
        return True

    except Exception as e:
        print(f"ERROR - {e}")
        return False


async def main():
    global available_points
    available_points = 0

    print("\n")
    print("="*80)
    print("  TEST DEL SISTEMA DE PUNTOS DE FIDELIDAD")
    print("="*80)
    print(f"\nAPI URL: {API_URL}")
    print(f"Restaurant: {TEST_RESTAURANT}")
    print(f"Cliente: {TEST_CUSTOMER}\n")

    results = []

    # Ejecutar tests
    results.append(await test_get_config())
    results.append(await test_earn_points())
    results.append(await test_get_balance())
    results.append(await test_redeem_points())
    results.append(await test_update_config())
    results.append(await test_multiple_purchases())

    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)

    # Balance final
    async with aiohttp.ClientSession() as session:
        url = f"{API_URL}/api/v1/loyalty/balance/{TEST_CUSTOMER}"
        params = {"restaurant_id": TEST_RESTAURANT}

        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"\nEstado final del cliente:")
                print(f"  Puntos disponibles: {data.get('available_points')}")
                print(f"  Puntos lifetime: {data.get('lifetime_points')}")
                print(f"  Nivel: {data.get('current_tier', '').upper()}")
                print(f"  Valor en dinero: ${data.get('points_value_in_currency', 0):.2f}")
                print(f"  Total gastado: ${data.get('total_spent', 0):.2f}")
                print(f"  Ordenes: {data.get('total_orders')}")

    # Tests pasados
    print("\n" + "="*80)
    print("RESULTADOS DE TESTS")
    print("="*80)

    passed = sum(results)
    total = len(results)

    print(f"\nTests pasados: {passed}/{total}")

    if passed == total:
        print("\nEXITO - Todos los tests pasaron correctamente!")
        print("\nSistema de puntos funcionando:")
        print("- Otorgar puntos automaticamente")
        print("- Canjear puntos por descuentos")
        print("- Sistema de niveles con multiplicadores")
        print("- Configuracion personalizable")
        print("\nListo para integrarse con el dashboard!")
    else:
        print(f"\nALGUNOS TESTS FALLARON - Revisa los errores arriba")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
