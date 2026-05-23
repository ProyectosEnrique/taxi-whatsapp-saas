"""
================================================================================
PATTERN LEARNER - APRENDIZAJE AUTOMÁTICO DE PATRONES REGEX
================================================================================
Sistema de auto-aprendizaje que usa LLM (Gemini/Cerebras) para:
1. Analizar casos donde regex falló y LLM tuvo éxito
2. Generar nuevos patrones regex automáticamente
3. Validar patrones antes de aplicarlos
4. Mantener historial de aprendizaje

Estrategia Híbrida:
- Análisis cada 5 casos fallidos O cada 12 horas (lo que ocurra primero)
- LLM genera candidatos de patrones
- Sistema valida con casos de prueba
- Patrones aprobados se agregan automáticamente

v1.0 - Diciembre 2024
================================================================================
"""

import re
import json
import logging
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


@dataclass
class FailedCase:
    """Caso donde regex falló y LLM tuvo que intervenir"""
    original_text: str
    expected_items: List[Dict]  # Items que LLM encontró
    regex_items: List[Dict]     # Items que regex encontró (parcial)
    fallback_reason: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'original_text': self.original_text,
            'expected_items': self.expected_items,
            'regex_items': self.regex_items,
            'fallback_reason': self.fallback_reason,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FailedCase':
        return cls(
            original_text=data['original_text'],
            expected_items=data['expected_items'],
            regex_items=data['regex_items'],
            fallback_reason=data['fallback_reason'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )


@dataclass
class PatternCandidate:
    """Patrón regex candidato generado por LLM"""
    pattern: str
    description: str
    example_matches: List[str]
    generated_from: List[str]  # Textos que originaron este patrón
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)
    validated: bool = False
    validation_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'pattern': self.pattern,
            'description': self.description,
            'example_matches': self.example_matches,
            'generated_from': self.generated_from,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat(),
            'validated': self.validated,
            'validation_score': self.validation_score
        }


@dataclass
class LearnedPattern:
    """Patrón aprendido y validado, listo para usar"""
    pattern: str
    description: str
    category: str  # 'differentiation', 'quantity', 'product', 'modifier'
    example_matches: List[str]
    times_used: int = 0
    success_rate: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'pattern': self.pattern,
            'description': self.description,
            'category': self.category,
            'example_matches': self.example_matches,
            'times_used': self.times_used,
            'success_rate': self.success_rate,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'LearnedPattern':
        return cls(
            pattern=data['pattern'],
            description=data['description'],
            category=data['category'],
            example_matches=data['example_matches'],
            times_used=data.get('times_used', 0),
            success_rate=data.get('success_rate', 1.0),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now()
        )


class PatternLearner:
    """
    Sistema de aprendizaje automático de patrones regex.

    Flujo:
    1. Registrar casos fallidos (regex parcial → LLM éxito)
    2. Cuando hay 5+ casos O pasaron 12 horas → analizar
    3. LLM genera patrones candidatos
    4. Validar patrones con casos de prueba
    5. Agregar patrones aprobados al parser
    """

    # Configuración por defecto
    DEFAULT_CONFIG = {
        'min_cases_for_analysis': 5,      # Mínimo de casos para analizar
        'analysis_interval_hours': 12,     # Horas entre análisis
        'min_validation_score': 0.8,       # Score mínimo para aprobar patrón
        'max_patterns_per_analysis': 3,    # Máximo de patrones a generar por análisis
        'data_dir': '/app/data/learning',  # Directorio para persistencia
    }

    def __init__(self, llm_provider=None, config: Dict = None):
        """
        Inicializa el sistema de aprendizaje.

        Args:
            llm_provider: Proveedor LLM (Gemini/Cerebras) para generar patrones
            config: Configuración personalizada
        """
        self.llm_provider = llm_provider
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # Estado interno
        self.failed_cases: List[FailedCase] = []
        self.pattern_candidates: List[PatternCandidate] = []
        self.learned_patterns: List[LearnedPattern] = []

        # Timestamps
        self.last_analysis_time: Optional[datetime] = None
        self.next_scheduled_analysis: Optional[datetime] = None

        # Lock para thread safety
        self._lock = threading.Lock()

        # Scheduler para análisis periódico
        self._scheduler_running = False
        self._scheduler_task = None

        # Cargar datos persistidos
        self._load_persisted_data()

        # Programar siguiente análisis
        self._schedule_next_analysis()

        logger.info(f"[LEARNER] Inicializado | Casos pendientes: {len(self.failed_cases)} | Patrones aprendidos: {len(self.learned_patterns)}")

    def _get_data_path(self, filename: str) -> Path:
        """Obtiene path para archivo de datos"""
        data_dir = Path(self.config['data_dir'])
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / filename

    def _load_persisted_data(self):
        """Carga datos persistidos del disco"""
        try:
            # Cargar casos fallidos pendientes
            cases_path = self._get_data_path('failed_cases.json')
            if cases_path.exists():
                with open(cases_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.failed_cases = [FailedCase.from_dict(c) for c in data]
                    logger.info(f"[LEARNER] Cargados {len(self.failed_cases)} casos pendientes")

            # Cargar patrones aprendidos
            patterns_path = self._get_data_path('learned_patterns.json')
            if patterns_path.exists():
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.learned_patterns = [LearnedPattern.from_dict(p) for p in data]
                    logger.info(f"[LEARNER] Cargados {len(self.learned_patterns)} patrones aprendidos")

            # Cargar timestamp de último análisis
            meta_path = self._get_data_path('metadata.json')
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    if meta.get('last_analysis_time'):
                        self.last_analysis_time = datetime.fromisoformat(meta['last_analysis_time'])

        except Exception as e:
            logger.error(f"[LEARNER] Error cargando datos persistidos: {e}")

    def _save_persisted_data(self):
        """Guarda datos al disco"""
        try:
            # Guardar casos fallidos
            cases_path = self._get_data_path('failed_cases.json')
            with open(cases_path, 'w', encoding='utf-8') as f:
                json.dump([c.to_dict() for c in self.failed_cases], f, ensure_ascii=False, indent=2)

            # Guardar patrones aprendidos
            patterns_path = self._get_data_path('learned_patterns.json')
            with open(patterns_path, 'w', encoding='utf-8') as f:
                json.dump([p.to_dict() for p in self.learned_patterns], f, ensure_ascii=False, indent=2)

            # Guardar metadata
            meta_path = self._get_data_path('metadata.json')
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'last_analysis_time': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
                    'total_patterns_learned': len(self.learned_patterns),
                    'pending_cases': len(self.failed_cases)
                }, f, ensure_ascii=False, indent=2)

            logger.debug("[LEARNER] Datos persistidos correctamente")

        except Exception as e:
            logger.error(f"[LEARNER] Error guardando datos: {e}")

    def register_failed_case(
        self,
        original_text: str,
        llm_items: List[Dict],
        regex_items: List[Dict],
        fallback_reason: str
    ):
        """
        Registra un caso donde regex falló parcialmente y LLM tuvo que intervenir.

        Args:
            original_text: Texto original del pedido
            llm_items: Items encontrados por LLM
            regex_items: Items encontrados por regex (parcial)
            fallback_reason: Razón del fallback
        """
        with self._lock:
            case = FailedCase(
                original_text=original_text,
                expected_items=llm_items,
                regex_items=regex_items,
                fallback_reason=fallback_reason
            )

            self.failed_cases.append(case)
            logger.info(f"[LEARNER] Caso registrado: '{original_text[:50]}...' | Razón: {fallback_reason}")

            # Persistir
            self._save_persisted_data()

            # Verificar si debemos analizar
            if self._should_analyze():
                logger.info("[LEARNER] Umbral alcanzado, iniciando análisis...")
                # Ejecutar análisis en background
                asyncio.create_task(self.analyze_and_learn())

    def _should_analyze(self) -> bool:
        """Determina si es momento de analizar casos"""
        # Condición 1: Suficientes casos acumulados
        if len(self.failed_cases) >= self.config['min_cases_for_analysis']:
            return True

        # Condición 2: Pasó el intervalo de tiempo
        if self.last_analysis_time:
            hours_since = (datetime.now() - self.last_analysis_time).total_seconds() / 3600
            if hours_since >= self.config['analysis_interval_hours'] and len(self.failed_cases) > 0:
                return True

        return False

    def _schedule_next_analysis(self):
        """Programa el siguiente análisis basado en tiempo"""
        if self.last_analysis_time:
            self.next_scheduled_analysis = self.last_analysis_time + timedelta(
                hours=self.config['analysis_interval_hours']
            )
        else:
            self.next_scheduled_analysis = datetime.now() + timedelta(
                hours=self.config['analysis_interval_hours']
            )

    async def analyze_and_learn(self) -> Dict[str, Any]:
        """
        Analiza casos fallidos y genera nuevos patrones.

        Proceso:
        1. Agrupar casos por razón de fallback
        2. Para cada grupo, pedir a LLM que genere patrón regex
        3. Validar patrones generados
        4. Agregar patrones aprobados

        Returns:
            Reporte del análisis
        """
        if not self.llm_provider or not self.llm_provider.is_available():
            logger.warning("[LEARNER] LLM no disponible para análisis")
            return {'error': 'LLM no disponible'}

        with self._lock:
            cases_to_analyze = self.failed_cases.copy()

        if not cases_to_analyze:
            logger.info("[LEARNER] No hay casos para analizar")
            return {'analyzed': 0, 'patterns_generated': 0}

        logger.info(f"[LEARNER] Iniciando análisis de {len(cases_to_analyze)} casos...")

        report = {
            'analyzed_cases': len(cases_to_analyze),
            'patterns_generated': 0,
            'patterns_validated': 0,
            'patterns_added': 0,
            'details': []
        }

        # Agrupar casos por razón
        cases_by_reason: Dict[str, List[FailedCase]] = {}
        for case in cases_to_analyze:
            reason = case.fallback_reason
            if reason not in cases_by_reason:
                cases_by_reason[reason] = []
            cases_by_reason[reason].append(case)

        # Analizar cada grupo
        for reason, cases in cases_by_reason.items():
            logger.info(f"[LEARNER] Analizando grupo '{reason}' con {len(cases)} casos")

            # Generar patrón para este grupo
            candidate = await self._generate_pattern_for_cases(reason, cases)

            if candidate:
                report['patterns_generated'] += 1

                # Validar patrón
                validation_result = self._validate_pattern(candidate, cases)

                if validation_result['score'] >= self.config['min_validation_score']:
                    candidate.validated = True
                    candidate.validation_score = validation_result['score']

                    # Crear patrón aprendido
                    learned = LearnedPattern(
                        pattern=candidate.pattern,
                        description=candidate.description,
                        category=self._categorize_pattern(reason),
                        example_matches=candidate.example_matches
                    )

                    self.learned_patterns.append(learned)
                    report['patterns_validated'] += 1
                    report['patterns_added'] += 1

                    logger.info(f"[LEARNER] Patrón aprobado: {candidate.pattern[:50]}...")

                    report['details'].append({
                        'reason': reason,
                        'pattern': candidate.pattern,
                        'score': validation_result['score'],
                        'status': 'approved'
                    })
                else:
                    logger.info(f"[LEARNER] Patrón rechazado (score: {validation_result['score']:.2f})")
                    report['details'].append({
                        'reason': reason,
                        'pattern': candidate.pattern,
                        'score': validation_result['score'],
                        'status': 'rejected',
                        'rejection_reason': validation_result.get('reason', 'score bajo')
                    })

        # Limpiar casos analizados
        with self._lock:
            self.failed_cases = [c for c in self.failed_cases if c not in cases_to_analyze]
            self.last_analysis_time = datetime.now()
            self._schedule_next_analysis()
            self._save_persisted_data()

        logger.info(f"[LEARNER] Análisis completado | Generados: {report['patterns_generated']} | Aprobados: {report['patterns_added']}")

        return report

    async def _generate_pattern_for_cases(
        self,
        reason: str,
        cases: List[FailedCase]
    ) -> Optional[PatternCandidate]:
        """
        Usa LLM para generar un patrón regex que cubra los casos fallidos.
        """
        # Preparar ejemplos para el prompt
        examples = []
        for case in cases[:5]:  # Máximo 5 ejemplos
            examples.append({
                'text': case.original_text,
                'expected': case.expected_items
            })

        examples_text = "\n".join([
            f"- Texto: \"{ex['text']}\"\n  Esperado: {json.dumps(ex['expected'], ensure_ascii=False)}"
            for ex in examples
        ])

        prompt = f"""Eres un experto en expresiones regulares para español mexicano.

CONTEXTO:
Tenemos un parser de pedidos de restaurante que usa regex. Los siguientes casos fallaron
y necesitamos un nuevo patrón regex para capturarlos.

RAZÓN DEL FALLO: {reason}

CASOS QUE FALLARON:
{examples_text}

TAREA:
Genera UN patrón regex en Python que capture estos casos.

REGLAS PARA EL PATRÓN:
1. Debe ser compatible con re.search() de Python
2. Usar grupos de captura para extraer: cantidad, producto, variante
3. Considerar variaciones del español mexicano (con/sin acentos)
4. Ser lo suficientemente general para casos similares
5. NO ser tan general que capture cosas incorrectas

FORMATO DE RESPUESTA (JSON válido, sin markdown):
{{
    "pattern": "el regex aquí",
    "description": "descripción corta de qué captura",
    "example_matches": ["ejemplo1", "ejemplo2"],
    "groups": ["grupo1_captura", "grupo2_captura"]
}}

Responde SOLO con el JSON, sin explicaciones adicionales."""

        try:
            response = self.llm_provider.generate(
                prompt=prompt,
                messages=[],
                temperature=0.2,
                max_tokens=500
            )

            response_text = response.get('response_text', '').strip()

            # Limpiar markdown si existe
            if response_text.startswith('```'):
                response_text = re.sub(r'^```\w*\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            # Parsear JSON
            parsed = json.loads(response_text)

            # Validar que el regex sea válido
            try:
                re.compile(parsed['pattern'])
            except re.error as e:
                logger.error(f"[LEARNER] Regex inválido generado: {e}")
                return None

            candidate = PatternCandidate(
                pattern=parsed['pattern'],
                description=parsed.get('description', ''),
                example_matches=parsed.get('example_matches', []),
                generated_from=[c.original_text for c in cases],
                confidence=0.8
            )

            logger.info(f"[LEARNER] Patrón candidato generado: {candidate.pattern[:80]}...")
            return candidate

        except json.JSONDecodeError as e:
            logger.error(f"[LEARNER] Error parseando respuesta LLM: {e}")
            return None
        except Exception as e:
            logger.error(f"[LEARNER] Error generando patrón: {e}")
            return None

    def _validate_pattern(
        self,
        candidate: PatternCandidate,
        cases: List[FailedCase]
    ) -> Dict[str, Any]:
        """
        Valida un patrón candidato contra los casos de prueba.

        Criterios:
        1. Debe hacer match con los casos originales
        2. No debe ser demasiado general (falsos positivos)
        3. Los grupos de captura deben extraer info útil
        """
        try:
            compiled = re.compile(candidate.pattern, re.IGNORECASE)
        except re.error:
            return {'score': 0.0, 'reason': 'regex inválido'}

        # Test 1: Match con casos originales
        matches = 0
        for case in cases:
            if compiled.search(case.original_text.lower()):
                matches += 1

        match_rate = matches / len(cases) if cases else 0

        # Test 2: Verificar falsos positivos con textos de control
        false_positives = 0
        control_texts = [
            "hola buenos días",
            "cuánto cuesta",
            "qué tienen de comer",
            "gracias por todo",
            "la cuenta por favor"
        ]

        for text in control_texts:
            if compiled.search(text.lower()):
                false_positives += 1

        false_positive_rate = false_positives / len(control_texts)

        # Test 3: Verificar que captura grupos útiles
        groups_useful = 0
        for case in cases[:3]:
            match = compiled.search(case.original_text.lower())
            if match and match.groups():
                # Al menos un grupo no vacío
                if any(g for g in match.groups() if g):
                    groups_useful += 1

        groups_rate = groups_useful / min(3, len(cases)) if cases else 0

        # Calcular score final
        score = (match_rate * 0.5) + ((1 - false_positive_rate) * 0.3) + (groups_rate * 0.2)

        result = {
            'score': round(score, 3),
            'match_rate': round(match_rate, 3),
            'false_positive_rate': round(false_positive_rate, 3),
            'groups_rate': round(groups_rate, 3)
        }

        if score < self.config['min_validation_score']:
            if match_rate < 0.6:
                result['reason'] = 'bajo match rate'
            elif false_positive_rate > 0.3:
                result['reason'] = 'muchos falsos positivos'
            else:
                result['reason'] = 'score general bajo'

        logger.info(f"[LEARNER] Validación: score={score:.2f}, match={match_rate:.2f}, fp={false_positive_rate:.2f}")

        return result

    def _categorize_pattern(self, reason: str) -> str:
        """Categoriza un patrón basado en la razón del fallback"""
        reason_lower = reason.lower()

        if 'diferenciacion' in reason_lower or 'anafor' in reason_lower:
            return 'differentiation'
        elif 'cantidad' in reason_lower:
            return 'quantity'
        elif 'segmento' in reason_lower or 'huerfano' in reason_lower:
            return 'product'
        else:
            return 'general'

    def get_learned_patterns(self) -> List[Dict]:
        """Retorna los patrones aprendidos para uso en el parser"""
        return [
            {
                'pattern': p.pattern,
                'category': p.category,
                'description': p.description
            }
            for p in self.learned_patterns
        ]

    def get_learning_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del sistema de aprendizaje"""
        return {
            'pending_cases': len(self.failed_cases),
            'learned_patterns': len(self.learned_patterns),
            'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'next_analysis': self.next_scheduled_analysis.isoformat() if self.next_scheduled_analysis else None,
            'config': {
                'min_cases': self.config['min_cases_for_analysis'],
                'interval_hours': self.config['analysis_interval_hours'],
                'min_validation_score': self.config['min_validation_score']
            },
            'patterns_by_category': self._count_patterns_by_category()
        }

    def _count_patterns_by_category(self) -> Dict[str, int]:
        """Cuenta patrones por categoría"""
        counts = {}
        for p in self.learned_patterns:
            counts[p.category] = counts.get(p.category, 0) + 1
        return counts

    def export_patterns_for_parser(self) -> str:
        """
        Exporta los patrones aprendidos en formato Python para agregar al parser.

        Útil para revisión manual antes de integrar permanentemente.
        """
        if not self.learned_patterns:
            return "# No hay patrones aprendidos aún"

        output = "# Patrones aprendidos automáticamente\n"
        output += f"# Generado: {datetime.now().isoformat()}\n\n"
        output += "LEARNED_PATTERNS = [\n"

        for p in self.learned_patterns:
            output += f"    {{\n"
            output += f"        'pattern': r'{p.pattern}',\n"
            output += f"        'category': '{p.category}',\n"
            output += f"        'description': '{p.description}',\n"
            output += f"        # Ejemplos: {p.example_matches[:2]}\n"
            output += f"    }},\n"

        output += "]\n"

        return output


# Instancia global (singleton)
_pattern_learner: Optional[PatternLearner] = None


def get_pattern_learner(llm_provider=None) -> PatternLearner:
    """Obtiene la instancia global del PatternLearner"""
    global _pattern_learner

    if _pattern_learner is None:
        _pattern_learner = PatternLearner(llm_provider=llm_provider)

    return _pattern_learner


def init_pattern_learner(llm_provider, config: Dict = None) -> PatternLearner:
    """Inicializa el PatternLearner con configuración específica"""
    global _pattern_learner
    _pattern_learner = PatternLearner(llm_provider=llm_provider, config=config)
    return _pattern_learner
