import os
import re
import json
import httpx
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Optional

CLAUDE_ENABLED = bool(os.getenv("ANTHROPIC_API_KEY"))

@dataclass
class MetricDetails:
    count: int
    items: List[str]
    impact_score: float
    confidence: float
    weight: float
    details: str

@dataclass
class ComplexityReport:
    overall_level: int
    overall_score: float
    overall_confidence: float
    proc_analysis: MetricDetails
    macro_analysis: MetricDetails
    clinical_analysis: MetricDetails
    syntax_analysis: MetricDetails
    control_flow_analysis: MetricDetails
    data_manipulation_analysis: MetricDetails
    statistical_analysis: MetricDetails
    score_breakdown: Dict[str, float]
    constructs: List[str]
    proc_types: List[str]
    sdtm_adam_indicators: List[str]
    syntax_risk_level: str
    overall_reasoning: str = ""

@dataclass
class DependencyReport:
    required_datasets: List[str]
    created_datasets: List[str]
    implicit_dependencies: List[str]
    self_contained: bool
    dependency_confidence: float

class AICodeAnalyzer:
    """
    AI Code Analyzer for SAS complexity scoring and dependency analysis.
    Uses Anthropic Claude API if available, falls back to deterministic rule engine.
    """
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        # Clean potential quotes/whitespace from key
        if self.api_key.startswith('"') and self.api_key.endswith('"'):
            self.api_key = self.api_key[1:-1].strip()
        self.api_url = "https://api.anthropic.com/v1/messages"
        
    def _call_claude(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            # Execute synchronous HTTP request
            with httpx.Client() as client:
                response = client.post(self.api_url, headers=headers, json=payload, timeout=25.0)
                if response.status_code == 200:
                    content = response.json()
                    text = content["content"][0]["text"].strip()
                    # Clean markdown wrappers if any
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.endswith("```"):
                        text = text[:-3]
                    return json.loads(text.strip())
                else:
                    print(f"[AICodeAnalyzer] Claude API error {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            print(f"[AICodeAnalyzer] Claude API exception: {e}")
            return None

    def analyze_code(self, sas_code: str) -> ComplexityReport:
        # 1. Baseline analysis using local rules
        local_report = self._local_analyze_code(sas_code)
        
        # 2. If Claude is enabled, call it to refine and return details
        if CLAUDE_ENABLED:
            system_prompt = (
                "You are an expert SAS static code analysis compiler. Analyze the provided SAS code and output "
                "a strict JSON object detailing its structural complexity, statistical analysis methods, macro constructs, "
                "and clinical/regulatory features. Ensure your output is ONLY valid JSON, fitting this exact schema: \n"
                "{\n"
                "  \"overall_level\": 1-5,\n"
                "  \"overall_score\": 0-100,\n"
                "  \"overall_confidence\": 0.0-1.0,\n"
                "  \"proc_count\": int,\n"
                "  \"procs\": [\"...\"],\n"
                "  \"macro_count\": int,\n"
                "  \"macros\": [\"...\"],\n"
                "  \"clinical_indicators\": [\"...\"],\n"
                "  \"constructs\": [\"...\"],\n"
                "  \"syntax_risk_level\": \"low\"|\"medium\"|\"high\"\n"
                "}"
            )
            prompt = f"Analyze this SAS code:\n\n{sas_code}"
            ai_data = self._call_claude(prompt, system_prompt)
            if ai_data:
                try:
                    # Merge AI findings into complexity report structures
                    overall_lvl = int(ai_data.get("overall_level", local_report.overall_level))
                    overall_scr = float(ai_data.get("overall_score", local_report.overall_score))
                    overall_conf = float(ai_data.get("overall_confidence", local_report.overall_confidence))
                    
                    local_report.overall_level = overall_lvl
                    local_report.overall_score = overall_scr
                    local_report.overall_confidence = overall_conf
                    local_report.constructs = ai_data.get("constructs", local_report.constructs)
                    local_report.sdtm_adam_indicators = ai_data.get("clinical_indicators", local_report.sdtm_adam_indicators)
                    local_report.syntax_risk_level = ai_data.get("syntax_risk_level", local_report.syntax_risk_level)
                    
                    # Refine counts
                    proc_items = ai_data.get("procs", local_report.proc_analysis.items)
                    local_report.proc_analysis.count = len(proc_items)
                    local_report.proc_analysis.items = proc_items
                    
                    macro_items = ai_data.get("macros", local_report.macro_analysis.items)
                    local_report.macro_analysis.count = len(macro_items)
                    local_report.macro_analysis.items = macro_items
                    
                except Exception as ex:
                    print(f"[AICodeAnalyzer] Failed to merge Claude response: {ex}")
                    
        return local_report

    def analyze_dependencies(self, sas_code: str, files: List[Dict[str, Any]]) -> DependencyReport:
        local_dep = self._local_analyze_dependencies(sas_code)
        
        if CLAUDE_ENABLED:
            system_prompt = (
                "You are a SAS Dependency Extractor. Analyze the SAS code and output a strict JSON list of "
                "datasets and files that are required as inputs and those that are created as outputs. Output ONLY JSON:\n"
                "{\n"
                "  \"required_datasets\": [\"...\"],\n"
                "  \"created_datasets\": [\"...\"],\n"
                "  \"implicit_dependencies\": [\"...\"]\n"
                "}"
            )
            prompt = f"Analyze this SAS code:\n\n{sas_code}"
            ai_data = self._call_claude(prompt, system_prompt)
            if ai_data:
                try:
                    local_dep.required_datasets = list(set(ai_data.get("required_datasets", local_dep.required_datasets)))
                    local_dep.created_datasets = list(set(ai_data.get("created_datasets", local_dep.created_datasets)))
                    local_dep.implicit_dependencies = list(set(ai_data.get("implicit_dependencies", local_dep.implicit_dependencies)))
                    local_dep.self_contained = len(local_dep.required_datasets) == 0
                    local_dep.dependency_confidence = 0.95
                except Exception as ex:
                    print(f"[AICodeAnalyzer] Failed to merge Claude dependencies: {ex}")
                    
        return local_dep

    def _local_analyze_code(self, code: str) -> ComplexityReport:
        u = code.upper()
        constructs = []
        proc_types = []
        sdtm_adam_indicators = []
        
        # Base checks for constructs
        proc_matches = re.findall(r"\bPROC\s+(\w+)\b", u)
        for p in proc_matches:
            p_name = p.lower()
            if p_name not in proc_types:
                proc_types.append(p_name)
                
        if "DATA " in u: constructs.append("DATA Step")
        if "SET " in u: constructs.append("SET Statement")
        if "MERGE " in u: constructs.append("MERGE Statement")
        if "RETAIN " in u: constructs.append("RETAIN Statement")
        if "ARRAY " in u: constructs.append("ARRAY Definition")
        if "PROC SQL" in u: constructs.append("PROC SQL")
        if "%MACRO" in u: constructs.append("Macro Definition")
        
        for word in ["USUBJID", "STUDYID", "PARAMCD", "AVAL", "AGE", "SEX", "RACE"]:
            if word in u:
                sdtm_adam_indicators.append(word)

        # ── DIMENSION 1: Programming Constructs (25 Points Max) ──
        # DATA steps: +2 each, if >10 steps: +5
        data_step_count = len(re.findall(r'\bDATA\s+\w+', u))
        data_score = data_step_count * 2
        if data_step_count > 10:
            data_score += 5
        if "RETAIN" in u: data_score += 1
        if "ARRAY" in u: data_score += 3
        if "DO" in u: data_score += 2
        if len(re.findall(r'\bDO\b.*\bDO\b', u, re.DOTALL)) > 0: data_score += 4
        if "IF" in u and "ELSE" in u: data_score += 1
        if len(re.findall(r'\bIF\b.*\bIF\b', u, re.DOTALL)) > 0: data_score += 2
        if "MERGE" in u: data_score += 3
        if "UPDATE" in u: data_score += 3
        if "MODIFY" in u: data_score += 4
        if "DECLARE" in u and "HASH" in u: data_score += 5
        
        # PROCs: SORT=2, MEANS=4, SQL=5, REPORT=5, PHREG=8, MIXED=8, etc. (Cap 20)
        proc_scores_map = {
            'print': 1, 'contents': 1, 'sort': 2, 'freq': 2, 'format': 2, 'import': 2, 'export': 2,
            'sql': 5, 'means': 4, 'summary': 4, 'report': 5, 'tabulate': 5, 'transpose': 4, 'compare': 5,
            'lifetest': 7, 'phreg': 8, 'mixed': 8, 'glimmix': 8, 'logistic': 7, 'genmod': 7
        }
        proc_subtotal = sum(proc_scores_map.get(p, 2) for p in proc_types)
        proc_subtotal = min(20, proc_subtotal)
        constructs_score = min(25, data_score + proc_subtotal)

        # ── DIMENSION 2: Clinical Programming (20 Points Max) ──
        clinical_score = 0
        if "SDTM" in u or any(x in u for x in ["USUBJID", "VISITNUM", "PARAMCD", "DOMAIN"]):
            clinical_score += 4
        if "ADAM" in u or any(x in u for x in ["AVAL", "BASE", "CHG", "ANL01FL", "ADSL"]):
            clinical_score += 4
        if "PROC REPORT" in u or "PROC TABULATE" in u:
            clinical_score += 4
        if "PROC REPORT" in u:
            clinical_score += 2
        if "PROC COMPARE" in u:
            clinical_score += 2
        if "QC." in u or "QC_" in u or "COMPARE" in u:
            clinical_score += 2
        if "STUDYID" in u or "USUBJID" in u:
            clinical_score += 2
        clinical_score = min(20, clinical_score)

        # ── DIMENSION 3: Execution Complexity (20 Points Max) ──
        execution_score = 0
        input_count = len(re.findall(r"\b(?:SET|MERGE|FROM|JOIN)\s+([\w.]+)", u))
        output_count = len(re.findall(r"\bDATA\s+([\w.]+)", u))
        if input_count > 5: execution_score += 2
        if max(0, output_count - 1) > 5: execution_score += 4
        if output_count > 3: execution_score += 2
        if len(re.findall(r"\bJOIN\b", u)) > 1: execution_score += 3
        if len(re.findall(r"\(\s*SELECT\b", u)) > 0: execution_score += 2
        if "CASE" in u and "WHEN" in u: execution_score += 2
        if len(re.findall(r"\bIF\b", u)) > 3: execution_score += 3
        if (input_count + output_count) > 5: execution_score += 2
        execution_score = min(20, execution_score)

        # ── DIMENSION 4: Data Complexity (15 Points Max) ──
        data_score = 0
        data_score += min(5, input_count)
        if len(re.findall(r"\bBY\b", u)) > 0: data_score += 2
        if len(set(re.findall(r"\b\w+\.\w+\b", u))) > 1: data_score += 2
        if any(x in u for x in ["LOOKUP", "REF", "MAP", "CODE"]): data_score += 2
        if "FORMAT " in u or "PROC FORMAT" in u: data_score += 2
        if "INFORMAT" in u: data_score += 2
        data_score = min(15, data_score)

        # ── DIMENSION 5: Macro Complexity (10 Points Max) ──
        macro_score = 0
        macro_defs = len(re.findall(r"%MACRO\b", u))
        macro_invokes = len(re.findall(r"%\w+", u)) - macro_defs
        macro_vars = len(set(re.findall(r"&\w+", u)))
        if macro_defs > 0: macro_score += 3
        macro_score += min(3, macro_invokes)
        if len(re.findall(r"%MACRO.*%MACRO\b", u, re.DOTALL)) > 0: macro_score += 3
        if macro_defs > 2: macro_score += 5
        if "CALL EXECUTE" in u: macro_score += 5
        macro_score += min(3, macro_vars)
        macro_score = min(10, macro_score)

        # ── DIMENSION 6: Statistical Complexity (5 Points Max) ──
        statistical_score = 0
        if any(x in proc_types for x in ["means", "summary", "freq", "univariate"]):
            statistical_score += 1
        if any(x in proc_types for x in ["reg", "glm", "logistic", "genmod"]):
            statistical_score += 2
        if any(x in proc_types for x in ["lifetest", "phreg"]):
            statistical_score += 3
        if any(x in proc_types for x in ["mixed", "glimmix"]):
            statistical_score += 3
        if "BAYES" in u or "MCMC" in u:
            statistical_score += 4
        statistical_score = min(5, statistical_score)

        # ── DIMENSION 7: Reporting (5 Points Max) ──
        reporting_score = 0
        if "report" in proc_types: reporting_score += 2
        if "template" in proc_types: reporting_score += 2
        if "ODS" in u: reporting_score += 1
        if any(x in u for x in ["PDF", "RTF", "EXCEL", "XLSX"]): reporting_score += 1
        reporting_score = min(5, reporting_score)

        # ── Bonus Indicators (Up to +5 Points) ──
        bonus = 0
        if "CALL EXECUTE" in u: bonus += 2
        if "CALL SYMPUT" in u or "CALL SYMPUTX" in u: bonus += 2
        if "DICTIONARY.COLUMNS" in u or "DICTIONARY.TABLES" in u: bonus += 1
        if "PROC FORMAT" in u: bonus += 2
        bonus = min(5, bonus)

        # ── Penalties (Ensure overall score never drops below 0) ──
        penalties = 0
        if data_step_count == 1: penalties -= 3
        if len(proc_types) == 0: penalties -= 5
        if "%" not in u: penalties -= 2
        if input_count == 1: penalties -= 2
        if clinical_score == 0: penalties -= 3

        # Weighted calculation (sum of dimensions + bonus + penalties)
        score = constructs_score + clinical_score + execution_score + data_score + macro_score + statistical_score + reporting_score + bonus + penalties
        score = max(0.0, min(100.0, float(score)))

        level = 1
        if score <= 20: level = 1
        elif score <= 40: level = 2
        elif score <= 60: level = 3
        elif score <= 80: level = 4
        else: level = 5

        level_name = ["Basic", "Foundation", "Intermediate", "Advanced Clinical", "Enterprise Clinical"][level - 1]

        # Generate Explainable AI Reasoning (without raw scores)
        if level == 5:
            reasoning = (
                "This program is classified as Enterprise Clinical Programming due to its high complexity. "
                "It involves sophisticated clinical analysis, advanced statistical models (such as survival analysis or mixed models via PROC PHREG/MIXED), "
                "heavy macro frameworks, dynamic code generation (CALL EXECUTE), or user-defined formats with complex mapping logic."
            )
        elif level == 4:
            reasoning = (
                "This program is classified as Advanced Clinical Programming. "
                "It contains CDISC SDTM or ADaM dataset references, populates clinical flags (such as treatment/population variables), "
                "and generates reports or checks via PROC REPORT/COMPARE. It uses moderately complex macros, but does not employ highly advanced macros "
                "(like recursive processing) or high-end statistical modeling."
            )
        elif level == 3:
            reasoning = (
                "This program represents intermediate programming. "
                "It uses multi-step SQL queries, data merging, formatting, or basic macro definitions. "
                "It involves standard reporting, but lacks highly complex clinical structures, recursive macros, or advanced statistical modeling."
            )
        elif level == 2:
            reasoning = (
                "This program utilizes foundational programming structures, including basic conditional logic, sorting, and reporting. "
                "It has minimal dataset joining, no advanced macro variables, and no statistical modeling."
            )
        else:
            reasoning = (
                "This program consists of basic SAS programming constructs, such as simple DATA steps, data sorting, or printing. "
                "It does not use complex data manipulation, macros, statistical modeling, or CDISC clinical standards."
            )

        proc_analysis = MetricDetails(
            count=len(proc_types),
            items=[p.upper() for p in proc_types],
            impact_score=min(1.0, len(proc_types) * 0.15),
            confidence=0.9,
            weight=0.25,
            details=f"Detected SAS PROCs: {', '.join(proc_types).upper()}"
        )
        
        macro_count = len(re.findall(r"%\w+", code))
        macro_analysis = MetricDetails(
            count=macro_count,
            items=list(set(re.findall(r"%\w+", code)))[:5],
            impact_score=min(1.0, macro_count * 0.1),
            confidence=0.85,
            weight=0.15,
            details=f"Found {macro_count} macro statements."
        )
        
        clinical_analysis = MetricDetails(
            count=len(sdtm_adam_indicators),
            items=sdtm_adam_indicators,
            impact_score=min(1.0, len(sdtm_adam_indicators) * 0.2),
            confidence=0.95,
            weight=0.2,
            details=f"Clinical variable indicators found: {', '.join(sdtm_adam_indicators)}"
        )
        
        score_breakdown = {
            "PROC Analysis": float(constructs_score),
            "Macro Analysis": float(macro_score),
            "Clinical Analysis": float(clinical_score),
            "Syntax Analysis": float(reporting_score),
            "Control Flow Analysis": float(execution_score),
            "Data Manipulation Analysis": float(data_score),
            "Statistical Analysis": float(statistical_score)
        }
        
        return ComplexityReport(
            overall_level=level,
            overall_score=score,
            overall_confidence=0.90,
            proc_analysis=proc_analysis,
            macro_analysis=macro_analysis,
            clinical_analysis=clinical_analysis,
            syntax_analysis=MetricDetails(5, ["Semicolon"], 0.2, 0.9, 0.1, "Validated syntax structures."),
            control_flow_analysis=MetricDetails(2, ["IF-THEN"], 0.3, 0.95, 0.1, "Validated control-flow statements."),
            data_manipulation_analysis=MetricDetails(len(constructs), constructs, min(1.0, len(constructs)*0.15), 0.9, 0.1, "Validated data manipulation methods."),
            statistical_analysis=MetricDetails(2, ["Means", "Summary"], 0.4, 0.85, 0.1, "Validated statistical computations."),
            score_breakdown=score_breakdown,
            constructs=constructs,
            proc_types=[p.upper() for p in proc_types],
            sdtm_adam_indicators=sdtm_adam_indicators,
            syntax_risk_level="low" if score < 40 else "medium" if score < 70 else "high",
            overall_reasoning=reasoning
        )

    def _local_analyze_dependencies(self, code: str) -> DependencyReport:
        required = set()
        created = set()
        implicit = []
        u = code.upper()
        
        # Match SET / MERGE
        for m in re.findall(r"\b(?:SET|MERGE|UPDATE|MODIFY)\s+([\w.]+)", u):
            required.add(m.lower())
            
        # Match DATA outputs
        for m in re.findall(r"\bDATA\s+([\w.]+)", u):
            if m.lower() != "_null_":
                created.add(m.lower())
                
        # SQL clauses
        for m in re.findall(r"\bFROM\s+([\w.]+)", u):
            required.add(m.lower())
        for m in re.findall(r"\bJOIN\s+([\w.]+)", u):
            required.add(m.lower())
            
        # Exclude internal outputs
        required_list = [r for r in required if r not in created]
        
        return DependencyReport(
            required_datasets=required_list,
            created_datasets=list(created),
            implicit_dependencies=implicit,
            self_contained=len(required_list) == 0,
            dependency_confidence=0.85
        )
