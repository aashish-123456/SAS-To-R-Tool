import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any

class DependencyType(Enum):
    DATASET = "dataset"
    FILE = "file"
    MACRO = "macro"
    FORMAT = "format"

class CriticalityLevel(Enum):
    CRITICAL = "critical"
    REQUIRED = "required"
    OPTIONAL = "optional"

@dataclass
class DependencyExplanation:
    criticality: CriticalityLevel
    purpose: str
    used_by: List[str]
    outputs_affected: List[str]
    translation_impact: str
    missing_consequences: str
    locations: List[int]

@dataclass
class DependencyItem:
    dep_type: DependencyType
    name: str
    explanation: DependencyExplanation
    confidence: float
    is_satisfied: bool

@dataclass
class AIDependencySummary:
    all_dependencies: List[DependencyItem]
    total: int
    satisfied: int
    missing: int
    readiness_percent: float
    by_type: Dict[str, int]
    by_criticality: Dict[str, int]
    dependency_confidence: float

class DependencyIntelligenceEngine:
    """
    AI Dependency Intelligence Engine. Analyzes code and extracts deep dependency relationships
    with explainability (purpose, outputs affected, consequences).
    """
    def analyze_dependencies(self, code: str) -> AIDependencySummary:
        u = code.upper()
        deps = []
        
        # 1. Discover SET / MERGE inputs
        for m in re.finditer(r"\b(?:SET|MERGE|UPDATE|MODIFY)\s+([\w.]+)", u):
            name = m.group(1).lower()
            # Find line number (approximate)
            line_no = code[:m.start()].count('\n') + 1
            
            # Formulate explanation based on CDISC naming patterns
            criticality = CriticalityLevel.REQUIRED
            purpose = f"Provides input variables to be processed in DATA step."
            outputs_affected = []
            
            if "dm" in name or "demographics" in name:
                criticality = CriticalityLevel.CRITICAL
                purpose = "Provides core demographic variables (USUBJID, AGE, SEX, RACE) used to derive SDTM DM and ADaM ADSL."
                outputs_affected = ["adam.adsl", "sdtm.dm"]
            elif "ae" in name or "adverse" in name:
                criticality = CriticalityLevel.CRITICAL
                purpose = "Provides safety event data for deriving treatment-emergent adverse event flags (TRTEMFL)."
                outputs_affected = ["adam.adae"]
                
            deps.append(DependencyItem(
                dep_type=DependencyType.DATASET,
                name=name,
                explanation=DependencyExplanation(
                    criticality=criticality,
                    purpose=purpose,
                    used_by=["DATA Step", "PROC SORT"],
                    outputs_affected=outputs_affected,
                    translation_impact="High - Translation of variables and grouping logic requires this schema.",
                    missing_consequences="Execution fails. R cannot resolve columns like USUBJID or calculate summary values.",
                    locations=[line_no]
                ),
                confidence=0.95,
                is_satisfied=False  # Initially upload is needed
            ))
            
        # 2. Discover SQL FROM/JOIN
        for m in re.finditer(r"\b(?:FROM|JOIN)\s+([\w.]+)", u):
            name = m.group(1).lower()
            if name in ["where", "on", "as", "outer", "inner", "left", "right", "full", "cross"]:
                continue
            line_no = code[:m.start()].count('\n') + 1
            
            deps.append(DependencyItem(
                dep_type=DependencyType.DATASET,
                name=name,
                explanation=DependencyExplanation(
                    criticality=CriticalityLevel.REQUIRED,
                    purpose="Input table referenced in PROC SQL join query.",
                    used_by=["PROC SQL"],
                    outputs_affected=[],
                    translation_impact="Medium",
                    missing_consequences="SQL query compilation failure.",
                    locations=[line_no]
                ),
                confidence=0.9,
                is_satisfied=False
            ))
            
        # De-duplicate by name
        seen = {}
        for d in deps:
            if d.name not in seen:
                seen[d.name] = d
            else:
                # Merge locations
                seen[d.name].explanation.locations = list(set(seen[d.name].explanation.locations + d.explanation.locations))
                
        all_deps = list(seen.values())
        
        # Calculate summary statistics
        total = len(all_deps)
        satisfied = sum(1 for d in all_deps if d.is_satisfied)
        missing = total - satisfied
        readiness = (satisfied / total * 100) if total > 0 else 100.0
        
        by_type = {"dataset": total}
        by_crit = {
            "critical": sum(1 for d in all_deps if d.explanation.criticality == CriticalityLevel.CRITICAL),
            "required": sum(1 for d in all_deps if d.explanation.criticality == CriticalityLevel.REQUIRED),
            "optional": sum(1 for d in all_deps if d.explanation.criticality == CriticalityLevel.OPTIONAL)
        }
        
        return AIDependencySummary(
            all_dependencies=all_deps,
            total=total,
            satisfied=satisfied,
            missing=missing,
            readiness_percent=round(readiness, 1),
            by_type=by_type,
            by_criticality=by_crit,
            dependency_confidence=0.92
        )
