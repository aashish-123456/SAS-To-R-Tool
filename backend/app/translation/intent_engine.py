"""
Engine 2 — Intent Engine
Answers: WHY does the SAS code exist?
Examines problem domain, goal, methodology, and expected outputs.
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

from .parser_engine import ParseResult


# ─────────────────────────────────────────────────────────────────────────────
# Domain indicator vocabulary
# ─────────────────────────────────────────────────────────────────────────────

_DOMAIN_INDICATORS: Dict[str, List[str]] = {
    "clinical": [
        # Require actual clinical terms — NOT generic demographic variables like age/weight/height
        # which appear in any general or function-testing code
        "patient", "heartrate", "temperature", "blood", "pressure",
        "dose", "treatment", "subject", "visit",
        "adverse", "event", "protocol", "sdtm", "adam", "usubjid", "subjid",
        "fever", "diagnosis", "symptom", "clinical", "hospital", "drug",
        "placebo", "endpoint", "baseline", "efficacy", "safety",
        "randomize", "cohort", "pharmacokinetics", "pharmacodynamics",
    ],
    "financial": [
        "revenue", "profit", "sales", "cost", "expense", "income",
        "budget", "forecast", "quarterly", "annual", "margin", "roi",
        "investment", "portfolio", "price", "stock", "equity", "asset",
        "liability", "balance", "ledger", "transaction", "fiscal",
    ],
    "retail": [
        "product", "category", "store", "region", "sales", "customer",
        "order", "quantity", "inventory", "sku", "promotion", "discount",
        "shelf", "brand", "supplier", "shipment",
    ],
    "hr": [
        "employee", "salary", "department", "hire", "position", "grade",
        "performance", "headcount", "turnover", "manager", "payroll",
        "benefits", "leave", "attendance", "appraisal",
    ],
    "survey": [
        "response", "question", "rating", "score", "survey", "likert",
        "respondent", "agree", "disagree", "strongly", "neutral",
        "questionnaire", "interview",
    ],
    "manufacturing": [
        "batch", "yield", "defect", "quality", "process", "machine",
        "unit", "production", "inspection", "tolerance", "spec",
    ],
}

# Patterns that indicate what the code is trying to DO
_GOAL_PATTERNS: Dict[str, List[str]] = {
    "dataset_creation": [
        r"\bdata\s+\w+\s*;.*?\binput\b",
        r"\bdata\s+\w+\s*;.*?\bdatalines\b",
        r"\bdata\s+\w+\s*;.*?\bcards\b",
    ],
    "data_transformation": [
        r"\bdata\s+\w+\s*;.*?\bset\b",
        r"\bdata\s+\w+\s*;.*?\bmerge\b",
        r"\bif\b.+?\bthen\b",
        r"\bretain\b",
        r"\barray\b",
    ],
    "statistical_analysis": [
        r"\bproc\s+means\b",
        r"\bproc\s+freq\b",
        r"\bproc\s+corr\b",
        r"\bproc\s+univariate\b",
    ],
    "regression_modeling": [
        r"\bproc\s+reg\b",
        r"\bproc\s+glm\b",
        r"\bproc\s+logistic\b",
        r"\bproc\s+mixed\b",
    ],
    "survival_analysis": [
        r"\bproc\s+phreg\b",
        r"\bproc\s+lifetest\b",
    ],
    "data_reporting": [
        r"\bproc\s+print\b",
        r"\bproc\s+report\b",
        r"\bproc\s+tabulate\b",
    ],
    "data_export": [r"\bproc\s+export\b"],
    "database_operations": [r"\bproc\s+sql\b"],
    "classification": [
        r"\bif\b.+?>\s*\d+.+?\bthen\b",
        r"\bif\b.+?<\s*\d+.+?\bthen\b",
        r"\bcase_when\b",
    ],
    "data_sorting": [r"\bproc\s+sort\b"],
    "data_reshaping": [r"\bproc\s+transpose\b"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OutputSegment:
    name: str
    description: str
    proc_type: str
    variables_involved: List[str]


@dataclass
class IntentResult:
    problem_domain: str
    primary_goal: str
    secondary_goals: List[str]
    problem_statement: str
    methodology: str
    expected_outputs: List[str]
    output_segments: List[OutputSegment]
    data_transformations: List[str]
    analysis_types: List[str]
    classification_logic: List[Dict]
    complexity_assessment: str
    domain_confidence: float
    key_metrics: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class IntentEngine:
    """
    Second sub-layer of the Translation Module.
    Examines the parsed SAS code to determine its PURPOSE — what problem
    it solves, what methodology it follows, and what outputs it produces.
    """

    def analyze(self, parse_result: ParseResult) -> IntentResult:
        domain, confidence = self._detect_domain(parse_result)
        primary_goal, secondary_goals = self._detect_goals(parse_result)
        output_segments = self._describe_outputs(parse_result)
        expected_outputs = [seg.description for seg in output_segments]

        return IntentResult(
            problem_domain      = domain,
            primary_goal        = primary_goal,
            secondary_goals     = secondary_goals,
            problem_statement   = self._generate_problem_statement(
                                      parse_result, domain, primary_goal, secondary_goals),
            methodology         = self._describe_methodology(parse_result),
            expected_outputs    = expected_outputs,
            output_segments     = output_segments,
            data_transformations= self._describe_transformations(parse_result),
            analysis_types      = self._classify_analysis(parse_result),
            classification_logic= self._extract_classification_logic(parse_result),
            complexity_assessment = self._assess_complexity(parse_result),
            domain_confidence   = confidence,
            key_metrics         = self._extract_key_metrics(parse_result),
        )

    # ── domain detection ───────────────────────────────────────────────────────

    def _detect_domain(self, pr: ParseResult) -> Tuple[str, float]:
        all_text = (pr.raw_code + " " + " ".join(pr.variables.keys())).lower()
        scores: Dict[str, int] = {}
        for domain, indicators in _DOMAIN_INDICATORS.items():
            score = sum(1 for kw in indicators if re.search(r'\b' + re.escape(kw) + r'\b', all_text))
            if score:
                scores[domain] = score
        # Heuristic: if the dataset name contains "demo", "test", "example" or the
        # code exercises many math/string functions without actual clinical procedures,
        # classify as general rather than forcing a weak domain match.
        dataset_names = ' '.join(pr.datasets.keys()).lower()
        function_code_signals = bool(
            re.search(r'\b(demo|test|example|sample|function)\b', dataset_names)
            or re.search(r'\b(demo|test|example|sample|function)\b', all_text[:200])
        )
        if function_code_signals and scores.get('clinical', 0) < 3:
            return "general", 0.6
        if not scores:
            return "general", 0.5
        best = max(scores, key=scores.get)          # type: ignore[arg-type]
        # Require at least 2 domain-specific matches to confidently assign a domain
        if scores[best] < 2:
            return "general", 0.4
        return best, min(scores[best] / 5.0, 1.0)

    # ── goal detection ─────────────────────────────────────────────────────────

    def _detect_goals(self, pr: ParseResult) -> Tuple[str, List[str]]:
        code = pr.raw_code
        goals: List[str] = []
        for goal, patterns in _GOAL_PATTERNS.items():
            for p in patterns:
                if re.search(p, code, re.IGNORECASE | re.DOTALL):
                    goals.append(goal)
                    break
        goals = list(dict.fromkeys(goals))  # deduplicate, preserve order
        if not goals:
            goals = ["data_analysis"]
        return goals[0], goals[1:]

    # ── problem statement ──────────────────────────────────────────────────────

    def _generate_problem_statement(
        self,
        pr: ParseResult,
        domain: str,
        primary_goal: str,
        secondary_goals: List[str],
    ) -> str:
        domain_desc = {
            "clinical":      "clinical/medical data",
            "financial":     "financial data",
            "retail":        "retail/sales data",
            "hr":            "human resources data",
            "survey":        "survey/questionnaire data",
            "manufacturing": "manufacturing/quality data",
            "general":       "data",
        }.get(domain, "data")

        datasets = list(pr.datasets.keys())
        ds_desc = (
            f" in dataset(s): {', '.join(datasets[:3])}"
            if datasets else ""
        )

        goal_desc = {
            "dataset_creation":    f"create and populate a {domain_desc} structure",
            "data_transformation": f"transform and derive new variables from {domain_desc}",
            "statistical_analysis":f"perform descriptive statistical analysis on {domain_desc}",
            "regression_modeling": f"build predictive regression models on {domain_desc}",
            "survival_analysis":   f"conduct survival / time-to-event analysis on {domain_desc}",
            "data_reporting":      f"generate formatted reports from {domain_desc}",
            "data_export":         f"export processed {domain_desc} to an external file",
            "database_operations": f"query and manipulate {domain_desc} using SQL",
            "classification":      f"classify and categorize records in {domain_desc}",
            "data_sorting":        f"sort {domain_desc}",
            "data_reshaping":      f"reshape / transpose {domain_desc}",
            "data_analysis":       f"analyze {domain_desc}",
        }.get(primary_goal, f"process {domain_desc}")

        parts = [f"The SAS code is designed to {goal_desc}{ds_desc}."]

        # Classification rules
        class_chains = [c for c in pr.if_else_chains if c.get("is_classification")]
        if class_chains:
            parts.append(
                f"It implements {len(class_chains)} classification rule(s) to "
                "categorize records based on conditional thresholds."
            )

        # Key variables
        if pr.variables:
            var_list = list(pr.variables.keys())[:5]
            parts.append(f"Key variables include: {', '.join(var_list)}.")

        # Proc usage
        if pr.proc_steps:
            proc_names = list({p["proc_type"] for p in pr.proc_steps})[:4]
            proc_str = ", ".join(f"PROC {n.upper()}" for n in proc_names)
            parts.append(
                f"The analysis uses {proc_str} to produce the required output."
            )

        # Secondary goals
        if secondary_goals:
            sec_desc = ", ".join(secondary_goals[:2]).replace("_", " ")
            parts.append(f"Additionally, the code performs {sec_desc}.")

        return " ".join(parts)

    # ── methodology ────────────────────────────────────────────────────────────

    def _describe_methodology(self, pr: ParseResult) -> str:
        steps: List[str] = []

        if pr.data_steps:
            steps.append("data is structured and prepared in SAS DATA steps")
        sort_found = any(p["proc_type"] == "sort" for p in pr.proc_steps)
        if sort_found:
            steps.append("sorted using PROC SORT")
        if pr.if_else_chains:
            steps.append("records are classified / filtered using IF-THEN-ELSE logic")
        if any(p["proc_type"] == "means" for p in pr.proc_steps):
            steps.append("descriptive statistics are computed with PROC MEANS")
        if any(p["proc_type"] == "freq" for p in pr.proc_steps):
            steps.append("frequency distributions are tabulated with PROC FREQ")
        if any(p["proc_type"] == "sql" for p in pr.proc_steps):
            steps.append("data is joined and queried via PROC SQL")
        if any(p["proc_type"] in ("reg", "glm", "logistic", "mixed") for p in pr.proc_steps):
            steps.append("statistical models are fitted")
        if any(p["proc_type"] == "print" for p in pr.proc_steps):
            steps.append("results are displayed with PROC PRINT")
        if any(p["proc_type"] == "export" for p in pr.proc_steps):
            steps.append("output is exported to a file")

        if not steps:
            return "The code processes data through standard SAS procedures."
        return "The methodology involves: " + "; then ".join(steps) + "."

    # ── output description ─────────────────────────────────────────────────────

    def _describe_outputs(self, pr: ParseResult) -> List[OutputSegment]:
        segments: List[OutputSegment] = []

        _proc_desc: Dict[str, str] = {
            "means":     "Descriptive statistics (N, Mean, Std, Min, Max) for selected variables",
            "freq":      "Frequency table with counts and percentages",
            "sort":      "Sorted dataset ordered by specified variables",
            "print":     "Formatted data listing",
            "sql":       "SQL query result set",
            "reg":       "Linear regression model with coefficients and R²",
            "glm":       "ANOVA / GLM model with F-statistics and p-values",
            "logistic":  "Logistic regression model with odds ratios and p-values",
            "mixed":     "Mixed model with fixed and random effects estimates",
            "phreg":     "Cox proportional hazards model output",
            "lifetest":  "Kaplan-Meier survival curves and log-rank test",
            "transpose": "Reshaped / transposed dataset",
            "export":    "Exported data file (CSV / Excel)",
            "corr":      "Correlation matrix between selected variables",
            "univariate":"Detailed univariate statistics and distribution summary",
        }

        for proc in pr.proc_steps:
            pt = proc["proc_type"]
            base = _proc_desc.get(pt, f"{pt.upper()} analysis output")
            # Enrich with variable list
            vars_used = proc.get("variables", [])
            if vars_used:
                base += f" for: {', '.join(str(v) for v in vars_used[:4])}"
            by_vars = proc.get("by_vars", [])
            if by_vars:
                base += f" (grouped by {', '.join(str(v) for v in by_vars[:3])})"
            segments.append(OutputSegment(
                name              = f"PROC {pt.upper()} Output",
                description       = base,
                proc_type         = pt,
                variables_involved= [str(v) for v in vars_used],
            ))

        # Data step outputs
        for ds in pr.data_steps:
            name = ds.get("dataset", "")
            if name and name.lower() not in ("_null_", "work"):
                segments.append(OutputSegment(
                    name              = f"Dataset: {name}",
                    description       = (
                        f"Processed dataset '{name}' created via DATA step "
                        f"with {len(ds.get('variables_defined', []))} derived variable(s)"
                    ),
                    proc_type         = "data_step",
                    variables_involved= ds.get("variables_defined", []),
                ))
        return segments

    # ── transformations ────────────────────────────────────────────────────────

    def _describe_transformations(self, pr: ParseResult) -> List[str]:
        ts: List[str] = []
        if pr.if_else_chains:
            ts.append(f"Conditional classification with {len(pr.if_else_chains)} IF-THEN-ELSE rule(s)")
        if pr.has_merge:
            ts.append("Dataset merging (MERGE)")
        if pr.has_retain:
            ts.append("Retaining variable values across observations (RETAIN)")
        if pr.has_array:
            ts.append("Array processing across multiple variables (ARRAY)")
        if pr.has_format:
            ts.append("Variable formatting and labeling (FORMAT)")
        if pr.do_loops:
            ts.append(f"Iterative processing with {len(pr.do_loops)} DO loop(s)")
        return ts

    # ── analysis type classification ───────────────────────────────────────────

    def _classify_analysis(self, pr: ParseResult) -> List[str]:
        types: List[str] = []
        if pr.statistics_requested:
            types.append("descriptive")
        if pr.has_proc_reg or pr.has_proc_glm:
            types.append("inferential")
        if pr.has_clinical_procs:
            types.append("clinical_biostatistics")
        if pr.has_sql:
            types.append("data_querying")
        if pr.if_else_chains:
            types.append("rule_based_classification")
        if pr.has_merge:
            types.append("data_integration")
        return types or ["exploratory"]

    # ── classification rule extraction ────────────────────────────────────────

    def _extract_classification_logic(self, pr: ParseResult) -> List[Dict]:
        return [
            {
                "condition":  c.get("condition", ""),
                "action":     c.get("then_action", ""),
                "else":       c.get("else_action", ""),
            }
            for c in pr.if_else_chains
            if c.get("is_classification")
        ]

    # ── complexity ─────────────────────────────────────────────────────────────

    def _assess_complexity(self, pr: ParseResult) -> str:
        score = (
            len(pr.data_steps)     * 1
            + len(pr.proc_steps)   * 2
            + len(pr.macros)       * 3
            + len(pr.if_else_chains) * 1
            + len(pr.do_loops)     * 2
            + (2 if pr.has_sql else 0)
            + (2 if pr.has_merge else 0)
            + (3 if pr.has_clinical_procs else 0)
            + (2 if pr.has_retain else 0)
            + (2 if pr.has_array else 0)
        )
        if score <= 5:  return "simple"
        if score <= 12: return "moderate"
        if score <= 20: return "complex"
        return "highly_complex"

    # ── key metrics ────────────────────────────────────────────────────────────

    def _extract_key_metrics(self, pr: ParseResult) -> List[str]:
        metrics: List[str] = []
        for proc in pr.proc_steps:
            for v in proc.get("variables", [])[:3]:
                sv = str(v)
                if sv not in metrics:
                    metrics.append(sv)
        if not metrics:
            metrics = list(pr.variables.keys())[:5]
        return metrics
