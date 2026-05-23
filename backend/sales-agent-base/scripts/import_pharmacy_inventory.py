#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de importación de inventario real de farmacia

Lee el archivo Excel y convierte los productos al formato del sistema RAG
"""

import sys
from pathlib import Path
import pandas as pd
import json
import re

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from services.pharmacy_rag import PharmacyRAGService
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_excel_inventory(excel_path: str) -> list:
    """
    Parsea el Excel de inventario y extrae productos con categorías

    Args:
        excel_path: Ruta al archivo Excel

    Returns:
        Lista de diccionarios con productos
    """
    # Leer Excel sin header
    df = pd.read_excel(excel_path, header=None)

    products = []
    current_category = "General"
    product_id = 1

    for idx, row in df.iterrows():
        col0 = row[0]
        col1 = row[1]

        # Saltar filas completamente vacías
        if pd.isna(col0) and pd.isna(col1):
            continue

        # Detectar categoría (tiene valor en col0 pero NaN en col1)
        if pd.notna(col0) and pd.isna(col1):
            current_category = str(col0).strip()
            logger.debug(f"Nueva categoría: {current_category}")
            continue

        # Saltar header "STOCK"
        if pd.notna(col1) and str(col1).strip().upper() == "STOCK":
            continue

        # Producto válido (tiene nombre y stock)
        if pd.notna(col0) and pd.notna(col1):
            try:
                name = str(col0).strip()
                stock = int(float(col1))

                # Saltar si el nombre parece inválido
                if not name or len(name) < 2:
                    continue

                # Inferir información del nombre
                product_info = extract_product_info(name, current_category)

                product = {
                    "id": str(product_id),
                    "name": name,
                    "description": product_info['description'],
                    "price": product_info['price'],
                    "category": current_category,
                    "generic_name": product_info['generic_name'],
                    "brand_name": product_info['brand_name'],
                    "active_ingredient": product_info['active_ingredient'],
                    "dosage": product_info['dosage'],
                    "presentation": product_info['presentation'],
                    "requires_prescription": product_info['requires_prescription'],
                    "controlled_substance": product_info['controlled_substance'],
                    "min_age": product_info['min_age'],
                    "symptoms": product_info['symptoms'],
                    "contraindications": [],
                    "side_effects": [],
                    "interactions": [],
                    "stock": stock,
                    "available": stock > 0
                }

                products.append(product)
                product_id += 1

            except Exception as e:
                logger.warning(f"Error procesando fila {idx}: {e}")
                continue

    logger.info(f"✅ Parseados {len(products)} productos en {len(set(p['category'] for p in products))} categorías")
    return products


def extract_product_info(name: str, category: str) -> dict:
    """
    Extrae información del nombre del producto

    Args:
        name: Nombre del producto
        category: Categoría del producto

    Returns:
        Dict con información extraída
    """
    name_upper = name.upper()

    # Detectar dosis (500MG, 100ML, etc)
    dosage_match = re.search(r'(\d+\.?\d*)\s*(MG|ML|G|L|MCG|UI|%)', name_upper)
    dosage = dosage_match.group(0) if dosage_match else None

    # Detectar presentación (CAP, TAB, INY, SUSP, etc)
    presentation_patterns = {
        'CAP': 'Cápsulas',
        'TAB': 'Tabletas',
        'INY': 'Inyectable',
        'SUSP': 'Suspensión',
        'SOL': 'Solución',
        'JBE': 'Jarabe',
        'GRAG': 'Grageas',
        'GEL': 'Gel',
        'CREMA': 'Crema',
        'POMADA': 'Pomada',
        'UNGÜENTO': 'Ungüento',
        'GOTAS': 'Gotas',
        'SPRAY': 'Spray'
    }

    presentation = None
    for pattern, full_name in presentation_patterns.items():
        if pattern in name_upper:
            presentation = full_name
            break

    # Precio estimado por categoría
    price_by_category = {
        'ANTIBIOTICOS': 180.0,
        'MEDICINA GENERAL': 120.0,
        'VITAMINAS': 150.0,
        'ANTIGRIPALES': 80.0,
        'ANTIGRIPAL SIN AZÚCAR': 85.0,
        'GOTAS': 90.0,
        'ANTIDIARRÉICOS': 65.0,
        'PATENTE': 200.0,
        'SUEROS': 30.0,
        'DESODORANTES': 45.0,
        'AGUA': 15.0
    }
    price = price_by_category.get(category, 100.0)

    # Determinar si requiere receta (antibióticos y algunos medicamentos)
    requires_prescription = False
    prescription_keywords = [
        'ANTIBIOTICO', 'AMOXICILI', 'AMIKACINA', 'CEFALEX', 'CLARITRO',
        'AZITRO', 'CIPRO', 'METRONIDAZOL', 'CLINDAMICINA', 'TETRACICLINA',
        'LOSARTÁN', 'ENALAPRIL', 'METFORMINA', 'GLIBENCLAMIDA', 'INSULINA',
        'CLONAZEPAM', 'DIAZEPAM', 'ALPRAZOLAM', 'LORAZEPAM'
    ]

    if category == 'ANTIBIOTICOS':
        requires_prescription = True
    else:
        for keyword in prescription_keywords:
            if keyword in name_upper:
                requires_prescription = True
                break

    # Sustancias controladas (ansiolíticos, sedantes)
    controlled_keywords = [
        'CLONAZEPAM', 'DIAZEPAM', 'ALPRAZOLAM', 'LORAZEPAM',
        'ZOLPIDEM', 'MIDAZOLAM', 'TRAMADOL', 'CODEINA'
    ]
    controlled_substance = any(keyword in name_upper for keyword in controlled_keywords)

    # Edad mínima
    min_age = 0
    if 'PEDIATR' in name_upper or 'NIÑOS' in name_upper or 'INFANTIL' in name_upper:
        min_age = 0
    elif 'ADULTO' in name_upper:
        min_age = 18
    elif requires_prescription or 'FORTE' in name_upper:
        min_age = 12

    # Extraer nombre genérico (simplificado - primera palabra significativa)
    words = name.split()
    generic_name = None
    if len(words) > 0:
        # Tomar primera palabra que no sea número o conectores
        for word in words:
            if len(word) > 3 and not word.isdigit():
                generic_name = word.title()
                break

    # Síntomas basados en categoría y nombre
    symptoms = infer_symptoms(name, category)

    # Descripción generada
    description = f"{presentation or 'Medicamento'}"
    if dosage:
        description += f" de {dosage.lower()}"
    description += f" para uso farmacéutico"

    return {
        'description': description,
        'price': price,
        'generic_name': generic_name,
        'brand_name': None,  # No tenemos info de marca vs genérico
        'active_ingredient': generic_name,  # Simplificado
        'dosage': dosage,
        'presentation': presentation,
        'requires_prescription': requires_prescription,
        'controlled_substance': controlled_substance,
        'min_age': min_age,
        'symptoms': symptoms
    }


def infer_symptoms(name: str, category: str) -> list:
    """Infiere síntomas basados en nombre y categoría"""
    symptoms = []
    name_upper = name.upper()

    # Mapeo de keywords a síntomas
    symptom_map = {
        'DOLOR': ['dolor'],
        'PARACETAMOL': ['dolor de cabeza', 'fiebre'],
        'IBUPROFENO': ['dolor muscular', 'inflamación', 'fiebre'],
        'GRIPA': ['gripa', 'resfriado'],
        'GRIPAL': ['gripa', 'resfriado', 'malestar general'],
        'TOS': ['tos'],
        'DIARR': ['diarrea'],
        'ESTOMAG': ['dolor de estómago'],
        'GASTRI': ['gastritis', 'acidez'],
        'ALERGIA': ['alergia'],
        'ALERGIC': ['alergia'],
        'VITAMIN': ['deficiencia vitamínica'],
        'ANTIBIOTICO': ['infección'],
        'AMOXICIL': ['infección respiratoria', 'infección'],
        'SUERO': ['deshidratación'],
        'ELECTROLIT': ['deshidratación', 'electrolitos bajos']
    }

    # Categorías a síntomas
    category_symptoms = {
        'ANTIGRIPALES': ['gripa', 'resfriado', 'congestión nasal'],
        'ANTIDIARRÉICOS': ['diarrea'],
        'VITAMINAS': ['deficiencia vitamínica', 'fatiga'],
        'ANTIBIOTICOS': ['infección bacteriana'],
        'SUEROS': ['deshidratación'],
        'GOTAS': ['irritación ocular', 'conjuntivitis']
    }

    # Buscar en nombre
    for keyword, symp_list in symptom_map.items():
        if keyword in name_upper:
            symptoms.extend(symp_list)

    # Agregar por categoría
    if category in category_symptoms:
        symptoms.extend(category_symptoms[category])

    # Eliminar duplicados y limitar
    symptoms = list(set(symptoms))[:5]

    return symptoms if symptoms else ['uso general']


def save_to_json(products: list, output_path: str):
    """Guarda productos a JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'version': '1.0',
            'source': 'INVENTARIO NUEVO FARMACIA 3 STOCK.xlsx',
            'total_products': len(products),
            'products': products
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Productos guardados en {output_path}")


def index_in_rag(products: list, tenant_id: str = "tenant_pharmacy_001"):
    """Indexa productos en el sistema RAG"""
    logger.info("🔄 Indexando productos en ChromaDB...")

    rag = PharmacyRAGService(tenant_id=tenant_id)

    if not rag.is_ready:
        logger.error("❌ RAG no está listo. Verificar instalación de chromadb")
        return False

    # Limpiar colección anterior
    logger.info("🗑️ Limpiando colección anterior...")
    rag.clear_collection()

    # Indexar productos reales
    count = rag.index_products(products)

    logger.info(f"✅ Indexados {count} productos")

    # Mostrar estadísticas
    stats = rag.get_stats()
    logger.info(f"📊 Estadísticas:")
    logger.info(f"   Total productos: {stats.get('total_products', 0)}")
    logger.info(f"   Colección: {stats.get('collection_name', '')}")

    return True


def main():
    """Ejecuta el proceso completo de importación"""
    logger.info("\n" + "=" * 60)
    logger.info("IMPORTACIÓN DE INVENTARIO REAL - FARMACIA")
    logger.info("=" * 60 + "\n")

    # Ruta al archivo Excel
    excel_path = r"C:\Users\ASUS\Downloads\INVENTARIO NUEVO FARMACIA 3 STOCK.xlsx"

    # 1. Parsear Excel
    logger.info("📖 Leyendo inventario desde Excel...")
    products = parse_excel_inventory(excel_path)

    if not products:
        logger.error("❌ No se encontraron productos en el Excel")
        return

    # 2. Guardar a JSON
    output_json = Path(__file__).parent.parent / 'config' / 'products_tenant_pharmacy_001.json'
    logger.info(f"💾 Guardando productos a JSON...")
    save_to_json(products, str(output_json))

    # 3. Indexar en RAG
    logger.info("🚀 Indexando en sistema RAG...")
    success = index_in_rag(products)

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✅ IMPORTACIÓN COMPLETADA EXITOSAMENTE")
        logger.info("=" * 60)
        logger.info(f"\n📊 Resumen:")
        logger.info(f"   • Total productos: {len(products)}")
        logger.info(f"   • Categorías: {len(set(p['category'] for p in products))}")
        logger.info(f"   • Con stock: {len([p for p in products if p['stock'] > 0])}")
        logger.info(f"   • Requieren receta: {len([p for p in products if p['requires_prescription']])}")
        logger.info(f"   • Sustancias controladas: {len([p for p in products if p['controlled_substance']])}")

        # Mostrar algunas categorías
        categories = {}
        for p in products:
            cat = p['category']
            categories[cat] = categories.get(cat, 0) + 1

        logger.info(f"\n📦 Top 10 categorías:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"   • {cat}: {count} productos")
    else:
        logger.error("❌ Error en la indexación")


if __name__ == "__main__":
    main()
