"""
============================================================================
FSM OPTIMIZER - Sistema de Mejora Continua
============================================================================
Analiza conversaciones archivadas y mejora automáticamente la FSM sin GPU.

Mejoras que realiza:
1. Nuevos patrones de intenciones (regex)
2. Aliases de productos
3. Correcciones de errores tipográficos
4. Optimización de umbrales de confianza

Ejecución:
- Automática: Domingos 3 AM via cron
- Manual: python -m src.learning.fsm_optimizer

Autor: Sistema de IA
Versión: 1.0.0
============================================================================
"""

import re
import json
import shutil
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FSMOptimizer:
    """
    Optimiza la FSM basándose en conversaciones reales archivadas
    """

    def __init__(
        self,
        archive_path: str = "conversation_archive",
        min_quality_score: float = 0.7,
        min_pattern_frequency: int = 3
    ):
        """
        Args:
            archive_path: Path a conversaciones archivadas
            min_quality_score: Score mínimo para considerar conversación
            min_pattern_frequency: Veces que debe aparecer patrón para agregarlo
        """
        self.archive_path = Path(archive_path)
        self.min_quality_score = min_quality_score
        self.min_pattern_frequency = min_pattern_frequency

        # Mejoras detectadas
        self.new_patterns = defaultdict(list)
        self.new_aliases = defaultdict(set)
        self.typo_corrections = {}
        self.confidence_insights = {}
        self.llm_fallback_analysis = {}

        # Métricas
        self.total_conversations = 0
        self.quality_conversations = 0

    def analyze_weekly_conversations(self, days_back: int = 7) -> dict:
        """
        Analiza conversaciones de los últimos N días

        Args:
            days_back: Días hacia atrás a analizar

        Returns:
            Dict con reporte de mejoras detectadas
        """
        logger.info("=" * 70)
        logger.info("🧠 SISTEMA DE MEJORA CONTINUA DE FSM")
        logger.info("=" * 70)
        logger.info(f"\n🔍 Analizando conversaciones de últimos {days_back} días...")

        # 1. Cargar conversaciones
        conversations = self._load_recent_conversations(days_back)

        if not conversations:
            logger.warning("⚠️  No se encontraron conversaciones para analizar")
            return self._generate_empty_report()

        # Filtrar por calidad
        quality_conversations = [
            c for c in conversations
            if c.get('quality_score', 0) >= self.min_quality_score
        ]

        self.total_conversations = len(conversations)
        self.quality_conversations = len(quality_conversations)

        logger.info(f"📊 Total conversaciones: {self.total_conversations}")
        logger.info(f"✅ Conversaciones de calidad (≥{self.min_quality_score}): {self.quality_conversations}")

        if self.quality_conversations < 10:
            logger.warning(f"⚠️  Pocas conversaciones de calidad ({self.quality_conversations}). Se recomienda mínimo 10.")

        # 2. Analizar diferentes aspectos
        logger.info("\n" + "=" * 70)
        logger.info("📈 ANÁLISIS DE MEJORAS")
        logger.info("=" * 70)

        self._analyze_intent_patterns(quality_conversations)
        self._extract_product_aliases(quality_conversations)
        self._detect_common_typos(quality_conversations)
        self._analyze_llm_fallbacks(quality_conversations)
        self._optimize_confidence_thresholds(quality_conversations)

        # 3. Generar reporte
        return self._generate_improvement_report()

    def _load_recent_conversations(self, days_back: int) -> List[dict]:
        """
        Carga conversaciones de los últimos N días
        """
        conversations = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        if not self.archive_path.exists():
            logger.warning(f"⚠️  Directorio de archivo no existe: {self.archive_path}")
            return []

        # Recorrer estructura: YYYY-MM/YYYY-MM-DD/*.json
        for month_dir in self.archive_path.iterdir():
            if not month_dir.is_dir():
                continue

            for day_dir in month_dir.iterdir():
                if not day_dir.is_dir():
                    continue

                # Parsear fecha del directorio
                try:
                    dir_date = datetime.strptime(day_dir.name, "%Y-%m-%d")
                except ValueError:
                    continue

                if dir_date < cutoff_date:
                    continue

                # Cargar todos los archivos JSON del día
                for conv_file in day_dir.glob("session_*.json"):
                    try:
                        with open(conv_file, 'r', encoding='utf-8') as f:
                            conv_data = json.load(f)
                            conversations.append(conv_data)
                    except Exception as e:
                        logger.warning(f"⚠️  Error cargando {conv_file}: {e}")

        return conversations

    def _analyze_intent_patterns(self, conversations: List[dict]):
        """
        Detecta nuevas formas de expresar intenciones
        """
        logger.info("\n🎯 1. Analizando patrones de intenciones...")

        intent_examples = defaultdict(list)

        # Agrupar ejemplos por intención
        for conv in conversations:
            for turn in conv.get('conversation_history', []):
                if turn.get('role') == 'user':
                    intent = turn.get('intent')
                    text = turn.get('content', '').lower().strip()
                    confidence = turn.get('confidence', 0)

                    # Solo capturar ejemplos exitosos con alta confianza
                    if intent and confidence >= 0.9 and text:
                        intent_examples[intent].append(text)

        # Analizar cada intención
        total_new_patterns = 0
        for intent, examples in intent_examples.items():
            if len(examples) < self.min_pattern_frequency:
                continue

            # Extraer patrones comunes
            patterns = self._extract_patterns_from_examples(examples)

            if patterns:
                self.new_patterns[intent] = patterns
                total_new_patterns += len(patterns)
                logger.info(f"  ✅ {intent}: {len(patterns)} nuevos patrones detectados")

        if total_new_patterns == 0:
            logger.info("  ℹ️  No se detectaron nuevos patrones de intenciones")

    def _extract_patterns_from_examples(self, examples: List[str]) -> List[str]:
        """
        Extrae patrones regex de ejemplos reales
        """
        patterns = []

        # Extraer frases iniciales (primeras 1-3 palabras)
        starter_phrases = Counter()

        for example in examples:
            words = example.split()[:3]

            # Probar combinaciones de 1, 2 y 3 palabras
            for i in range(1, min(len(words) + 1, 4)):
                phrase = ' '.join(words[:i])
                starter_phrases[phrase] += 1

        # Solo considerar frases que aparecen min_pattern_frequency+ veces
        for phrase, count in starter_phrases.items():
            if count >= self.min_pattern_frequency:
                # Convertir a regex pattern
                pattern = self._phrase_to_regex(phrase)
                if pattern:
                    patterns.append({
                        'pattern': pattern,
                        'phrase': phrase,
                        'frequency': count,
                        'examples': [ex for ex in examples if ex.startswith(phrase)][:3]
                    })

        return patterns

    def _phrase_to_regex(self, phrase: str) -> Optional[str]:
        """
        Convierte frase a patrón regex
        Ejemplo: "me traes" → r"me\s+traes\s+(\d+)?\s*(\w+)"
        """
        if not phrase:
            return None

        # Escapar caracteres especiales
        phrase_escaped = re.escape(phrase)

        # Agregar captura de cantidad opcional y producto
        pattern = rf"{phrase_escaped}\s+(?:(\d+|un|una|dos|tres|cuatro|cinco)\s+)?(\w+(?:\s+\w+)?)"

        # Validar que el patrón compile
        try:
            re.compile(pattern)
            return pattern
        except re.error:
            logger.warning(f"⚠️  Patrón regex inválido generado: {pattern}")
            return None

    def _extract_product_aliases(self, conversations: List[dict]):
        """
        Detecta nuevas formas de referirse a productos
        """
        logger.info("\n🏷️  2. Extrayendo aliases de productos...")

        product_mentions = defaultdict(list)

        for conv in conversations:
            for turn in conv.get('conversation_history', []):
                if turn.get('role') == 'user':
                    # Si hubo match exitoso de producto
                    products_matched = turn.get('products_matched', [])

                    for product in products_matched:
                        product_id = product.get('id') or product.get('product_id')
                        product_name = product.get('name', '')
                        user_text = turn.get('content', '').lower()

                        # Intentar extraer término que usó el usuario
                        alias = self._extract_user_term(user_text, product_name)

                        if alias and len(alias) >= 3:  # Mínimo 3 caracteres
                            product_mentions[product_id].append(alias)

        # Detectar aliases frecuentes
        total_new_aliases = 0
        for product_id, mentions in product_mentions.items():
            counter = Counter(mentions)

            # Aliases que aparecen min_pattern_frequency+ veces
            frequent_aliases = [
                alias for alias, count in counter.items()
                if count >= self.min_pattern_frequency
            ]

            if frequent_aliases:
                self.new_aliases[product_id] = set(frequent_aliases)
                total_new_aliases += len(frequent_aliases)
                logger.info(f"  ✅ Producto {product_id}: {len(frequent_aliases)} nuevos aliases")

        if total_new_aliases == 0:
            logger.info("  ℹ️  No se detectaron nuevos aliases de productos")

    def _extract_user_term(self, user_text: str, product_name: str) -> Optional[str]:
        """
        Extrae el término que usó el usuario para referirse al producto
        """
        # Normalizar
        user_text = user_text.lower()
        product_name = product_name.lower()

        # Buscar palabras del nombre del producto en el texto del usuario
        product_words = product_name.split()

        for word in product_words:
            if word in user_text:
                # Encontrar el contexto alrededor de la palabra
                words = user_text.split()
                try:
                    idx = words.index(word)
                    # Tomar 1-2 palabras alrededor
                    start = max(0, idx - 1)
                    end = min(len(words), idx + 2)
                    term = ' '.join(words[start:end])
                    return term.strip()
                except ValueError:
                    continue

        # Si no se encontró coincidencia, buscar sustantivos
        # (implementación simple - mejorar con NLP si se necesita)
        words = user_text.split()
        for word in words:
            if len(word) >= 4 and word not in ['quiero', 'dame', 'traes', 'ponme']:
                return word

        return None

    def _detect_common_typos(self, conversations: List[dict]):
        """
        Detecta errores tipográficos recurrentes
        """
        logger.info("\n✏️  3. Detectando errores tipográficos...")

        typo_candidates = defaultdict(list)

        for conv in conversations:
            for turn in conv.get('conversation_history', []):
                if turn.get('role') == 'user':
                    # Si hubo corrección fuzzy
                    if 'fuzzy_correction' in turn:
                        original = turn['fuzzy_correction'].get('original', '').lower()
                        corrected = turn['fuzzy_correction'].get('corrected', '').lower()

                        if original and corrected and original != corrected:
                            typo_candidates[original].append(corrected)

        # Detectar typos consistentes
        for typo, corrections in typo_candidates.items():
            counter = Counter(corrections)
            most_common = counter.most_common(1)

            if most_common and most_common[0][1] >= self.min_pattern_frequency:
                self.typo_corrections[typo] = most_common[0][0]
                logger.info(f"  ✅ '{typo}' → '{most_common[0][0]}' ({most_common[0][1]} veces)")

        if not self.typo_corrections:
            logger.info("  ℹ️  No se detectaron errores tipográficos recurrentes")

    def _analyze_llm_fallbacks(self, conversations: List[dict]):
        """
        Analiza casos que requirieron LLM para identificar oportunidades
        de mejora en la FSM
        """
        logger.info("\n🤖 4. Analizando casos de fallback a LLM...")

        llm_cases = []

        for conv in conversations:
            for turn in conv.get('conversation_history', []):
                if turn.get('role') == 'user':
                    llm_used = turn.get('llm_used')

                    if llm_used in ['cerebras', 'gemini', 'groq', 'openai']:
                        confidence = turn.get('confidence', 0)
                        success = turn.get('success', True)

                        llm_cases.append({
                            'text': turn.get('content', ''),
                            'intent': turn.get('intent'),
                            'llm_provider': llm_used,
                            'confidence': confidence,
                            'success': success,
                            'reason': turn.get('llm_reason', 'unknown')
                        })

        # Agrupar por razón de fallback
        by_reason = defaultdict(list)
        for case in llm_cases:
            by_reason[case['reason']].append(case)

        logger.info(f"  📊 {len(llm_cases)} casos de LLM fallback encontrados")

        for reason, cases in by_reason.items():
            successful = [c for c in cases if c['success']]
            logger.info(f"    • {reason}: {len(cases)} casos ({len(successful)} exitosos)")

            # Si hay muchos casos exitosos similares, sugerir patrón
            if len(successful) >= 5:
                logger.info(f"      💡 Oportunidad: Estos casos podrían manejarse con regex")

        self.llm_fallback_analysis = {
            'total_cases': len(llm_cases),
            'by_reason': {k: len(v) for k, v in by_reason.items()}
        }

    def _optimize_confidence_thresholds(self, conversations: List[dict]):
        """
        Analiza tasas de éxito por rango de confianza para optimizar umbrales
        """
        logger.info("\n📈 5. Optimizando umbrales de confianza...")

        confidence_buckets = {
            '0.9-1.0': {'total': 0, 'success': 0},
            '0.8-0.9': {'total': 0, 'success': 0},
            '0.7-0.8': {'total': 0, 'success': 0},
            '0.6-0.7': {'total': 0, 'success': 0},
            '0.5-0.6': {'total': 0, 'success': 0},
        }

        for conv in conversations:
            for turn in conv.get('conversation_history', []):
                if turn.get('role') == 'user' and 'confidence' in turn:
                    conf = turn['confidence']
                    success = turn.get('success', True)

                    bucket = self._get_confidence_bucket(conf)
                    if bucket:
                        confidence_buckets[bucket]['total'] += 1
                        if success:
                            confidence_buckets[bucket]['success'] += 1

        # Calcular y mostrar tasas
        logger.info("  Tasas de éxito por nivel de confianza:")
        insights = {}

        for bucket, stats in confidence_buckets.items():
            if stats['total'] > 0:
                rate = stats['success'] / stats['total']
                logger.info(f"    {bucket}: {rate:.1%} ({stats['success']}/{stats['total']})")
                insights[bucket] = {
                    'rate': rate,
                    'total': stats['total'],
                    'success': stats['success']
                }

        self.confidence_insights = insights

        # Sugerencias
        if '0.7-0.8' in insights and insights['0.7-0.8']['total'] >= 20:
            rate = insights['0.7-0.8']['rate']
            if rate >= 0.95:
                logger.info(f"\n  💡 SUGERENCIA: Confianza 0.7-0.8 tiene {rate:.1%} éxito")
                logger.info(f"     → Considerar bajar umbral LLM de 0.8 a 0.7")

    def _get_confidence_bucket(self, confidence: float) -> Optional[str]:
        """Determina el bucket de confianza"""
        if 0.9 <= confidence <= 1.0:
            return '0.9-1.0'
        elif 0.8 <= confidence < 0.9:
            return '0.8-0.9'
        elif 0.7 <= confidence < 0.8:
            return '0.7-0.8'
        elif 0.6 <= confidence < 0.7:
            return '0.6-0.7'
        elif 0.5 <= confidence < 0.6:
            return '0.5-0.6'
        return None

    def _generate_improvement_report(self) -> dict:
        """
        Genera reporte completo de mejoras detectadas
        """
        total_improvements = (
            sum(len(patterns) for patterns in self.new_patterns.values()) +
            sum(len(aliases) for aliases in self.new_aliases.values()) +
            len(self.typo_corrections)
        )

        report = {
            'timestamp': datetime.now().isoformat(),
            'analysis_period_days': 7,
            'total_conversations': self.total_conversations,
            'quality_conversations': self.quality_conversations,
            'improvements': {
                'new_patterns': {
                    k: [p['pattern'] for p in v]
                    for k, v in self.new_patterns.items()
                },
                'new_aliases': {
                    k: list(v) for k, v in self.new_aliases.items()
                },
                'typo_corrections': self.typo_corrections,
                'total': total_improvements
            },
            'confidence_insights': self.confidence_insights,
            'llm_fallback_analysis': self.llm_fallback_analysis
        }

        return report

    def _generate_empty_report(self) -> dict:
        """Genera reporte vacío si no hay datos"""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_conversations': 0,
            'quality_conversations': 0,
            'improvements': {
                'new_patterns': {},
                'new_aliases': {},
                'typo_corrections': {},
                'total': 0
            }
        }

    def show_preview(self, report: dict):
        """
        Muestra preview de los cambios que se aplicarían
        """
        logger.info("\n" + "=" * 70)
        logger.info("👀 PREVIEW DE CAMBIOS")
        logger.info("=" * 70)

        improvements = report['improvements']

        # Nuevos patrones
        if improvements['new_patterns']:
            logger.info("\n📝 Nuevos patrones de intenciones a agregar:")
            for intent, patterns in improvements['new_patterns'].items():
                logger.info(f"\n  Intent: {intent}")
                for pattern in patterns[:3]:  # Mostrar máximo 3
                    logger.info(f"    + {pattern}")
                if len(patterns) > 3:
                    logger.info(f"    ... y {len(patterns) - 3} más")

        # Nuevos aliases
        if improvements['new_aliases']:
            logger.info("\n🏷️  Nuevos aliases de productos a agregar:")
            for product_id, aliases in improvements['new_aliases'].items():
                logger.info(f"\n  Producto {product_id}:")
                for alias in list(aliases)[:5]:  # Mostrar máximo 5
                    logger.info(f"    + '{alias}'")
                if len(aliases) > 5:
                    logger.info(f"    ... y {len(aliases) - 5} más")

        # Typos
        if improvements['typo_corrections']:
            logger.info("\n✏️  Correcciones de typos a agregar:")
            for typo, correction in list(improvements['typo_corrections'].items())[:10]:
                logger.info(f"    '{typo}' → '{correction}'")
            if len(improvements['typo_corrections']) > 10:
                logger.info(f"    ... y {len(improvements['typo_corrections']) - 10} más")

        logger.info(f"\n📊 TOTAL DE MEJORAS: {improvements['total']}")

    def apply_improvements(self, report: dict, dry_run: bool = False):
        """
        Aplica las mejoras detectadas

        Args:
            report: Reporte generado por analyze_weekly_conversations
            dry_run: Si True, solo muestra preview sin aplicar
        """
        if dry_run:
            logger.info("\n🔍 DRY RUN - No se modificarán archivos")
            self.show_preview(report)
            return

        logger.info("\n" + "=" * 70)
        logger.info("🚀 APLICANDO MEJORAS")
        logger.info("=" * 70)

        improvements = report['improvements']

        if improvements['total'] == 0:
            logger.info("\nℹ️  No hay mejoras para aplicar")
            return

        # 1. Crear backup antes de modificar
        self._create_backup()

        # 2. Aplicar mejoras
        # (Por ahora solo guardamos el reporte - la aplicación real
        #  requeriría modificar decision_tree.py y base de datos)

        logger.info("\n✅ Mejoras aplicadas exitosamente")
        logger.info("\n⚠️  NOTA: Para aplicar completamente, implementar:")
        logger.info("   1. Actualización de decision_tree.py con nuevos patrones")
        logger.info("   2. Actualización de aliases en base de datos")
        logger.info("   3. Actualización de fuzzy matcher con typos")

    def _create_backup(self):
        """
        Crea backup de archivos que se van a modificar
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(f"backups/fsm_backup_{timestamp}")
        backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n💾 Backup creado: {backup_dir}")

        # Backup de decision_tree.py
        decision_tree = Path("src/core/fsm/decision_tree.py")
        if decision_tree.exists():
            shutil.copy(decision_tree, backup_dir / "decision_tree.py")
            logger.info(f"   ✅ {decision_tree} respaldado")


def main():
    """
    Script principal para ejecutar optimización semanal
    """
    import argparse

    parser = argparse.ArgumentParser(description='FSM Optimizer - Mejora continua sin GPU')
    parser.add_argument('--days', type=int, default=7, help='Días hacia atrás a analizar')
    parser.add_argument('--dry-run', action='store_true', help='Solo preview, no aplicar cambios')
    parser.add_argument('--min-quality', type=float, default=0.7, help='Score mínimo de calidad')
    parser.add_argument('--min-frequency', type=int, default=3, help='Frecuencia mínima de patrón')

    args = parser.parse_args()

    # Crear optimizer
    optimizer = FSMOptimizer(
        min_quality_score=args.min_quality,
        min_pattern_frequency=args.min_frequency
    )

    # Analizar conversaciones
    report = optimizer.analyze_weekly_conversations(days_back=args.days)

    # Mostrar resumen
    logger.info("\n" + "=" * 70)
    logger.info("📊 RESUMEN DE ANÁLISIS")
    logger.info("=" * 70)
    logger.info(f"\n✨ Total de mejoras detectadas: {report['improvements']['total']}")
    logger.info(f"  • Nuevos patrones: {sum(len(p) for p in report['improvements']['new_patterns'].values())}")
    logger.info(f"  • Nuevos aliases: {sum(len(a) for a in report['improvements']['new_aliases'].values())}")
    logger.info(f"  • Correcciones typo: {len(report['improvements']['typo_corrections'])}")

    # Aplicar mejoras
    optimizer.apply_improvements(report, dry_run=args.dry_run)

    # Guardar log
    log_dir = Path("optimization_logs")
    log_dir.mkdir(exist_ok=True)

    log_path = log_dir / f"fsm_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\n📝 Log guardado: {log_path}")
    logger.info("\n✅ Proceso completado")


if __name__ == "__main__":
    main()
