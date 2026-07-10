"""
REvolveS SAS Code Complexity Scoring Engine
Weighted scoring system based on programming constructs, clinical context, and data complexity.

Score Range:
- Level 1 (Basic): 0-20
- Level 2 (Simple): 21-40
- Level 3 (Intermediate): 41-60
- Level 4 (Advanced Clinical): 61-80
- Level 5 (Enterprise): 81-100
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of complexity score"""
    data_steps: int = 0
    procs: Dict[str, int] = field(default_factory=dict)  # {proc_type: score}
    sql_features: Dict[str, int] = field(default_factory=dict)  # {feature: score}
    macros: Dict[str, int] = field(default_factory=dict)  # {feature: count/score}
    clinical: Dict[str, int] = field(default_factory=dict)  # {feature: count/score}
    dataset_complexity: Dict[str, int] = field(default_factory=dict)  # {type: count}
    logic: Dict[str, int] = field(default_factory=dict)  # {feature: score}
    reporting: Dict[str, int] = field(default_factory=dict)  # {feature: score}

    def total_score(self) -> int:
        """Calculate total score from all components"""
        total = 0

        # Add data steps (integer)
        if isinstance(self.data_steps, int):
            total += self.data_steps

        # Add all dict-based scores
        for component in [self.procs, self.sql_features, self.macros, self.clinical,
                         self.dataset_complexity, self.logic, self.reporting]:
            if isinstance(component, dict):
                try:
                    component_sum = sum(int(v) for v in component.values() if isinstance(v, (int, float)))
                    total += component_sum
                except (TypeError, ValueError):
                    pass

        return total


class ComplexityScorer:
    """Weighted complexity scoring engine for SAS code"""

    # PROC Score Map
    PROC_SCORES = {
        'print': 2, 'contents': 2,
        'sort': 3, 'freq': 3, 'format': 3,
        'import': 4, 'export': 4,
        'means': 5, 'summary': 5, 'transpose': 5,
        'sql': 8, 'report': 8, 'compare': 8, 'tabulate': 8, 'univariate': 8,
        'lifetest': 12, 'phreg': 12, 'mixed': 12, 'glimmix': 12,
        'logistic': 10, 'genmod': 10,
    }

    # Statistical PROCs (higher value)
    STATISTICAL_PROCS = {'logistic', 'genmod', 'lifetest', 'phreg', 'mixed', 'glimmix'}

    def __init__(self):
        pass

    def score(self, sas_code: str) -> Tuple[int, ScoreBreakdown]:
        """
        Calculate complexity score (0-100) with breakdown.
        Returns: (total_score, breakdown)
        """
        code_upper = sas_code.upper()
        breakdown = ScoreBreakdown()

        # 1. DATA Steps
        data_steps = len(re.findall(r'\bDATA\s+\w+', code_upper))
        if data_steps > 10:
            breakdown.data_steps = data_steps * 2 + 5
        else:
            breakdown.data_steps = data_steps * 2

        # 2. PROC Statements
        procs_found = re.findall(r'\bPROC\s+(\w+)', code_upper)
        unique_procs = set(p.lower() for p in procs_found)
        for proc in unique_procs:
            score = self.PROC_SCORES.get(proc, 5)  # Default: 5 if unknown
            breakdown.procs[proc] = score

        # 3. SQL Features
        if 'SQL' in unique_procs:
            joins = len(re.findall(r'\bJOIN\b', code_upper))
            group_by = len(re.findall(r'\bGROUP\s+BY\b', code_upper))
            union = len(re.findall(r'\bUNION\b', code_upper))
            subqueries = len(re.findall(r'\(\s*SELECT\b', code_upper))
            case_when = len(re.findall(r'\bCASE\s+WHEN\b', code_upper))

            if joins > 0:
                breakdown.sql_features['joins'] = joins * 2
            if group_by > 0:
                breakdown.sql_features['group_by'] = group_by * 2
            if union > 0:
                breakdown.sql_features['union'] = union * 2
            if subqueries > 0:
                breakdown.sql_features['subqueries'] = subqueries * 3
            if case_when > 0:
                breakdown.sql_features['case_when'] = case_when * 2

        # 4. Macro Usage
        macro_defs = len(re.findall(r'%MACRO\b', code_upper))
        macro_invokes = len(re.findall(r'%[A-Za-z_]\w*\s*\(', code_upper))
        macro_vars = len(set(re.findall(r'&[A-Za-z_]\w*', sas_code)))
        nested_macros = len(re.findall(r'%MACRO.*%MACRO\b', code_upper, re.DOTALL))
        call_execute = len(re.findall(r'\bCALL\s+EXECUTE\b', code_upper))

        if macro_defs > 0:
            breakdown.macros['definitions'] = macro_defs * 8
        if macro_invokes > 0:
            breakdown.macros['invocations'] = macro_invokes * 2
        if macro_vars > 0:
            breakdown.macros['variables'] = min(macro_vars, 10)  # Cap at 10
        if nested_macros > 0:
            breakdown.macros['nested'] = nested_macros * 5
        if call_execute > 0:
            breakdown.macros['call_execute'] = call_execute * 10

        # 5. Clinical Programming
        sdtm_refs = self._count_unique_datasets(code_upper, r'\bSDTM\.|USUBJID|VISITNUM|PARAMCD|DOMAIN')
        adam_refs = self._count_unique_datasets(code_upper, r'\bADAM\.|AVAL|BASE|CHG|ANL01FL')
        tlf_gen = 1 if re.search(r'\bPROC\s+(REPORT|TABULATE)\b', code_upper) else 0
        proc_report = 1 if re.search(r'\bPROC\s+REPORT\b', code_upper) else 0
        proc_compare = 1 if re.search(r'\bPROC\s+COMPARE\b', code_upper) else 0
        treatment_vars = len(re.findall(r'\b(TRT|TRTPN|ARM|ARMN)\b', code_upper))
        pop_flags = len(re.findall(r'\b(SAFFL|ITTFL|PPROTFL|COMPLFL|RANDFL)\b', code_upper))
        ods = 1 if re.search(r'\bODS\s+(OUTPUT|HTML|PDF|RTF)\b', code_upper) else 0

        if sdtm_refs > 0:
            breakdown.clinical['sdtm'] = sdtm_refs * 5
        if adam_refs > 0:
            breakdown.clinical['adam'] = adam_refs * 5
        if tlf_gen > 0:
            breakdown.clinical['tlf'] = 6
        if proc_report > 0:
            breakdown.clinical['proc_report'] = 5
        if proc_compare > 0:
            breakdown.clinical['proc_compare'] = 5
        if treatment_vars > 0:
            breakdown.clinical['treatment_vars'] = min(treatment_vars * 2, 10)
        if pop_flags > 0:
            breakdown.clinical['pop_flags'] = min(pop_flags * 2, 10)
        if ods > 0:
            breakdown.clinical['ods'] = 3

        # 6. Dataset Complexity
        input_datasets = len(re.findall(r'\b(SET|MERGE|UPDATE|FROM|JOIN)\s+\w+', code_upper))
        output_datasets = len(re.findall(r'\bDATA\s+([\w.]+)', code_upper))
        intermediate_datasets = max(0, output_datasets - 1)  # Estimate

        if input_datasets > 0:
            breakdown.dataset_complexity['input'] = input_datasets
        if output_datasets > 0:
            breakdown.dataset_complexity['output'] = output_datasets
        if intermediate_datasets > 0:
            breakdown.dataset_complexity['intermediate'] = intermediate_datasets * 2

        # 7. Programming Logic
        if_count = len(re.findall(r'\bIF\b', code_upper))
        nested_if = len(re.findall(r'\bIF\b.*\bIF\b', code_upper))
        do_loops = len(re.findall(r'\bDO\b', code_upper))
        nested_loops = len(re.findall(r'\bDO\b.*\bDO\b', code_upper))
        arrays = len(re.findall(r'\bARRAY\b', code_upper))
        retain = len(re.findall(r'\bRETAIN\b', code_upper))
        merge = len(re.findall(r'\bMERGE\b', code_upper))
        update = len(re.findall(r'\bUPDATE\b', code_upper))
        modify = len(re.findall(r'\bMODIFY\b', code_upper))

        if if_count > 0:
            breakdown.logic['if'] = if_count
        if nested_if > 0:
            breakdown.logic['nested_if'] = nested_if * 2
        if do_loops > 0:
            breakdown.logic['do'] = do_loops * 2
        if nested_loops > 0:
            breakdown.logic['nested_loops'] = nested_loops * 4
        if arrays > 0:
            breakdown.logic['arrays'] = arrays * 5
        if retain > 0:
            breakdown.logic['retain'] = retain * 2
        if merge > 0:
            breakdown.logic['merge'] = merge * 3
        if update > 0:
            breakdown.logic['update'] = update * 3
        if modify > 0:
            breakdown.logic['modify'] = modify * 4

        # 8. Reporting
        proc_template = 1 if re.search(r'\bPROC\s+TEMPLATE\b', code_upper) else 0
        pdf = 1 if re.search(r'\bODS\s+PDF\b', code_upper) else 0
        excel = 1 if re.search(r'\b(EXCEL|EXCELXP)\b', code_upper) else 0
        rtf = 1 if re.search(r'\bODS\s+RTF\b', code_upper) else 0

        if proc_template > 0:
            breakdown.reporting['proc_template'] = 5
        if pdf > 0:
            breakdown.reporting['pdf'] = 2
        if excel > 0:
            breakdown.reporting['excel'] = 2
        if rtf > 0:
            breakdown.reporting['rtf'] = 2

        # Calculate final score (capped at 100)
        total_score = min(breakdown.total_score(), 100)

        return total_score, breakdown

    def _count_unique_datasets(self, code_upper: str, pattern: str) -> int:
        """Count unique dataset references matching pattern"""
        matches = set(re.findall(rf'{pattern}', code_upper))
        return len(matches)

    def get_level(self, score: int) -> int:
        """Get complexity level (1-5) from score"""
        if score <= 20:
            return 1
        elif score <= 40:
            return 2
        elif score <= 60:
            return 3
        elif score <= 80:
            return 4
        else:
            return 5

    def get_level_name(self, level: int) -> str:
        """Get human-readable level name"""
        names = {
            1: "Basic",
            2: "Simple",
            3: "Intermediate",
            4: "Advanced Clinical",
            5: "Enterprise",
        }
        return names.get(level, "Unknown")
