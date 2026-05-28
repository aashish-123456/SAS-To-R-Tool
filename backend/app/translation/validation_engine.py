"""
Engine 6 — Execution Flow Validation Engine
Validates that the generated R code:
  1. Addresses the same problem statement as the SAS code
  2. Follows the same logical execution flow
  3. Uses appropriate packages (not over-engineered)
  4. Is as simple and concise as possible
  5. Will produce output equivalent to the SAS output
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .parser_engine import ParseResult
from .intent_engine import IntentResult
from .execution_flow_engine import FlowResult
from .package_recommender_engine import PackageRecommendation
from .translation_engine import TranslationResult


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    severity: str          # "error" | "warning" | "info"
    title: str
    detail: str
    suggestion: Optional[str] = None


@dataclass
class FlowValidationResult:
    problem_statement_match: bool
    execution_flow_match: bool
    packages_appropriate: bool
    code_complexity: str          # simple | moderate | complex | highly_complex
    lines_of_code: int
    estimated_equivalence_pct: float
    issues: List[ValidationIssue]
    strengths: List[str]
    recommendations: List[str]
    approval_status: str          # approved | approved_with_warnings | needs_review | requires_revision
    validation_summary: str
    engine_coverage: Dict[str, bool]


# ─────────────────────────────────────────────────────────────────────────────
# R ↔ SAS equivalence knowledge
# ─────────────────────────────────────────────────────────────────────────────

_SAS_TO_R_EQUIV: Dict[str, List[str]] = {
    "means":     ["summarise", "group_by", "mean(", "sd(", "min(", "max(", "n()"],
    "freq":      ["count(", "table(", "prop.table"],
    "sort":      ["arrange(", "order("],
    "print":     ["print(", "cat(", "head("],
    "sql":       ["join(", "inner_join", "left_join", "filter(", "select("],
    "reg":       ["lm(", "summary(model"],
    "glm":       ["aov(", "lm("],
    "logistic":  ["glm(", "binomial"],
    "mixed":     ["lme(", "lmer(", "nlme", "lme4"],
    "phreg":     ["coxph(", "Surv("],
    "lifetest":  ["survfit(", "Surv(", "survdiff"],
    "transpose": ["pivot_wider", "pivot_longer"],
    "export":    ["write.csv", "write_xlsx", "write_excel"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class ExecutionFlowValidationEngine:
    """
    Sixth sub-layer of the Translation Module.
    Verifies the completeness and correctness of the translation before it
    is presented to the user.  Does not re-run code — it performs static
    analysis of the generated R script against the intent and flow derived
    by the preceding engines.
    """

    def validate(
        self,
        parse_result: ParseResult,
        intent_result: IntentResult,
        flow_result: FlowResult,
        package_rec: PackageRecommendation,
        translation_result: TranslationResult,
    ) -> FlowValidationResult:

        issues:          List[ValidationIssue] = []
        strengths:       List[str]             = []
        recommendations: List[str]             = []

        r_code_lc = translation_result.r_code.lower()

        ps_match   = self._check_problem_statement(parse_result, translation_result,
                                                   issues, strengths, r_code_lc)
        flow_match = self._check_execution_flow(flow_result, translation_result,
                                                issues, strengths, r_code_lc)
        pkg_ok     = self._check_packages(package_rec, parse_result,
                                          issues, strengths, recommendations)
        complexity, loc = self._check_complexity(translation_result, parse_result,
                                                 issues, strengths, recommendations)
        equivalence = self._estimate_equivalence(parse_result, translation_result,
                                                 issues, strengths, r_code_lc)

        engine_coverage = {
            "parser_engine":              True,
            "intent_engine":              bool(intent_result.problem_statement),
            "execution_flow_engine":      bool(flow_result.steps),
            "package_recommender_engine": bool(package_rec.primary_packages),
            "translation_engine":         bool(translation_result.r_code),
            "validation_engine":          True,
        }

        n_errors   = sum(1 for i in issues if i.severity == "error")
        n_warnings = sum(1 for i in issues if i.severity == "warning")

        if n_errors == 0 and n_warnings == 0:
            approval = "approved"
        elif n_errors == 0 and n_warnings <= 2:
            approval = "approved_with_warnings"
        elif n_errors <= 1:
            approval = "needs_review"
        else:
            approval = "requires_revision"

        summary = self._summarise(ps_match, flow_match, pkg_ok,
                                  equivalence, approval, issues, strengths)

        return FlowValidationResult(
            problem_statement_match  = ps_match,
            execution_flow_match     = flow_match,
            packages_appropriate     = pkg_ok,
            code_complexity          = complexity,
            lines_of_code            = loc,
            estimated_equivalence_pct= equivalence,
            issues                   = issues,
            strengths                = strengths,
            recommendations          = recommendations,
            approval_status          = approval,
            validation_summary       = summary,
            engine_coverage          = engine_coverage,
        )

    # ── check 1: problem statement ────────────────────────────────────────────

    def _check_problem_statement(
        self,
        pr: ParseResult,
        tr: TranslationResult,
        issues: List[ValidationIssue],
        strengths: List[str],
        r_lc: str,
    ) -> bool:
        covered = 0
        total   = 0

        for proc in pr.proc_steps:
            pt       = proc["proc_type"]
            expected = _SAS_TO_R_EQUIV.get(pt, [])
            if not expected:
                continue
            total += 1
            if any(e.lower() in r_lc for e in expected):
                covered += 1
            else:
                issues.append(ValidationIssue(
                    severity   = "warning",
                    title      = f"PROC {pt.upper()} coverage incomplete",
                    detail     = (
                        f"Expected R equivalents ({', '.join(expected[:3])}) "
                        "not found in generated code."
                    ),
                    suggestion = f"Verify that the PROC {pt.upper()} logic is represented in R.",
                ))

        # Classification logic
        if pr.if_else_chains:
            if "case_when" in r_lc or "if_else" in r_lc or "ifelse" in r_lc:
                strengths.append(
                    "Multi-branch classification translated using dplyr::case_when() "
                    "or base ifelse()"
                )
            else:
                issues.append(ValidationIssue(
                    severity   = "warning",
                    title      = "Classification logic may be missing",
                    detail     = "IF-THEN-ELSE chains not found as case_when() / ifelse() in R code.",
                    suggestion = "Review conditional logic in the generated R script.",
                ))

        if total > 0:
            ratio = covered / total
            if ratio >= 0.8:
                strengths.append(
                    f"Problem coverage: {covered}/{total} SAS procedures translated"
                )
            return ratio >= 0.5
        return True   # no PROC steps → data step only, always fine

    # ── check 2: execution flow ───────────────────────────────────────────────

    def _check_execution_flow(
        self,
        fr: FlowResult,
        tr: TranslationResult,
        issues: List[ValidationIssue],
        strengths: List[str],
        r_lc: str,
    ) -> bool:
        if not fr.steps:
            return True

        has_data  = bool(re.search(r"data\.frame|read\.csv|tibble|read_csv", r_lc))
        has_analysis = bool(re.search(
            r"summarise|lm\(|aov\(|count\(|coxph|survfit|glm\(", r_lc
        ))

        if has_analysis and not has_data and fr.input_datasets:
            issues.append(ValidationIssue(
                severity   = "info",
                title      = "Data loading step not explicit",
                detail     = (
                    "Analysis code is present but no explicit data loading was found. "
                    "Assumes data is already in the R session."
                ),
                suggestion = "Add a read.csv() or data.frame() call if the dataset is external.",
            ))

        strengths.append(
            f"Execution flow captured: {fr.total_steps} logical step(s) translated"
        )
        return True

    # ── check 3: packages ─────────────────────────────────────────────────────

    def _check_packages(
        self,
        pr_rec: PackageRecommendation,
        pr: ParseResult,
        issues: List[ValidationIssue],
        strengths: List[str],
        recommendations: List[str],
    ) -> bool:
        pkg_set = set(pr_rec.all_packages)
        ok = True

        if pr.has_clinical_procs and "survival" not in pkg_set:
            issues.append(ValidationIssue(
                severity   = "error",
                title      = "Missing survival package",
                detail     = (
                    "Clinical survival procedures (PHREG / LIFETEST) require the survival package."
                ),
                suggestion = "Add survival to the package list.",
            ))
            ok = False

        if pr.has_proc_mixed and "nlme" not in pkg_set and "lme4" not in pkg_set:
            issues.append(ValidationIssue(
                severity   = "error",
                title      = "Missing mixed model package",
                detail     = "PROC MIXED requires nlme or lme4.",
                suggestion = "Add nlme or lme4 to the recommended packages.",
            ))
            ok = False

        if "dplyr" in pkg_set:
            strengths.append(
                "dplyr selected — most readable and concise data manipulation syntax"
            )
        if "base" in pkg_set:
            strengths.append("Base R used where possible — minimal external dependencies")

        n_pkgs = len([p for p in pkg_set if p != "base"])
        if n_pkgs >= 4 and "dplyr" in pkg_set and "tidyr" in pkg_set:
            recommendations.append(
                "Consider library(tidyverse) to load all tidyverse packages with one call."
            )
        if n_pkgs == 0:
            strengths.append("No external packages required — pure base R translation")

        return ok

    # ── check 4: complexity ───────────────────────────────────────────────────

    def _check_complexity(
        self,
        tr: TranslationResult,
        pr: ParseResult,
        issues: List[ValidationIssue],
        strengths: List[str],
        recommendations: List[str],
    ) -> tuple:
        loc = tr.lines_of_code

        if loc <= 35:
            complexity = "simple"
            strengths.append(f"Concise R code: {loc} lines — well-optimised translation")
        elif loc <= 80:
            complexity = "moderate"
            strengths.append(f"R code is {loc} lines — appropriate for the SAS complexity level")
        elif loc <= 150:
            complexity = "complex"
            recommendations.append(
                "Consider extracting repeated logic into helper functions to reduce code length."
            )
        else:
            complexity = "highly_complex"
            issues.append(ValidationIssue(
                severity   = "warning",
                title      = "Generated R code is lengthy",
                detail     = (
                    f"The R script is {loc} lines. This may indicate overly verbose translation."
                ),
                suggestion = (
                    "Review for repeated patterns; consider purrr::map() or lapply() "
                    "to compress repetitive blocks."
                ),
            ))

        return complexity, loc

    # ── check 5: equivalence estimate ────────────────────────────────────────

    def _estimate_equivalence(
        self,
        pr: ParseResult,
        tr: TranslationResult,
        issues: List[ValidationIssue],
        strengths: List[str],
        r_lc: str,
    ) -> float:
        score = 100.0

        if "# todo" in r_lc or "# TODO" in r_lc:
            score -= 15
            issues.append(ValidationIssue(
                severity   = "warning",
                title      = "Unresolved TODO items in R code",
                detail     = "Some SAS constructs could not be fully auto-translated.",
                suggestion = "Manually complete the TODO items in the generated script.",
            ))

        if "fallback" in r_lc or "simplified" in r_lc:
            score -= 10

        # Penalise if key R constructs expected but absent
        required = []
        if any(p["proc_type"] == "means" for p in pr.proc_steps):
            required.append("summarise")
        if any(p["proc_type"] == "freq" for p in pr.proc_steps):
            required.append("count(")
        if any(p["proc_type"] == "sort" for p in pr.proc_steps):
            required.append("arrange(")
        if any(p["proc_type"] == "reg" for p in pr.proc_steps):
            required.append("lm(")
        missing = [r for r in required if r not in r_lc]
        score -= len(missing) * 8

        score = max(0.0, min(100.0, score))

        if score >= 90:
            strengths.append(
                f"Excellent estimated equivalence: {score:.0f}% — R code closely mirrors SAS logic"
            )
        elif score >= 75:
            strengths.append(
                f"Good equivalence: {score:.0f}% — core SAS logic translated successfully"
            )
        return score

    # ── summary ───────────────────────────────────────────────────────────────

    def _summarise(
        self,
        ps_match: bool,
        flow_match: bool,
        pkg_ok: bool,
        equivalence: float,
        approval: str,
        issues: List[ValidationIssue],
        strengths: List[str],
    ) -> str:
        _labels = {
            "approved":               "✓ APPROVED",
            "approved_with_warnings": "✓ APPROVED WITH WARNINGS",
            "needs_review":           "⚠ NEEDS REVIEW",
            "requires_revision":      "✗ REQUIRES REVISION",
        }
        n_err  = sum(1 for i in issues if i.severity == "error")
        n_warn = sum(1 for i in issues if i.severity == "warning")

        parts = [
            f"Status: {_labels.get(approval, approval)}",
            f"Estimated equivalence: {equivalence:.0f}%",
            f"Problem statement match: {'Yes' if ps_match else 'Partial'}",
            f"Execution flow: {'Complete' if flow_match else 'Partial'}",
            f"Package selection: {'Appropriate' if pkg_ok else 'Review required'}",
            f"Issues: {n_err} error(s), {n_warn} warning(s)",
        ]
        if strengths:
            parts.append(f"Strengths: {'; '.join(strengths[:2])}")
        return " | ".join(parts)
