"""
Engine 5 — Translation Engine
Collates all prior engine outputs and generates the final, optimised R code.
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

from .parser_engine import ParseResult
from .intent_engine import IntentResult
from .execution_flow_engine import FlowResult
from .package_recommender_engine import PackageRecommendation


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TranslationResult:
    r_code: str             # complete R script (header + install + library + body)
    r_code_body: str        # just the translation body (no install/library preamble)
    install_code: str       # auto-install block
    library_code: str       # library() block
    annotations: List[str]  # intent-level comments added to the script
    warnings: List[str]     # issues the user should review manually
    translation_notes: List[str]
    packages_used: List[str]
    lines_of_code: int


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class TranslationEngine:
    """
    Fifth sub-layer of the Translation Module.
    Uses insights from all four preceding engines to produce the cleanest,
    most correct R translation of the SAS input code.
    """

    def translate(
        self,
        parse_result: ParseResult,
        intent_result: IntentResult,
        flow_result: FlowResult,
        package_rec: PackageRecommendation,
    ) -> TranslationResult:

        warnings: List[str]           = []
        translation_notes: List[str]  = []

        # ── 1.  Generate R body via existing AST-based generator ───────────────
        r_body = self._ast_generate(parse_result, warnings)

        # ── 2.  Apply package-aware post-processing ────────────────────────────
        r_body = self._post_process(r_body, parse_result, package_rec)

        # ── 3.  Build structured header ────────────────────────────────────────
        header       = self._header(intent_result, flow_result, package_rec)
        install_code = package_rec.install_code
        library_code = package_rec.library_code

        # ── 4.  Assemble full script ───────────────────────────────────────────
        full_parts = [
            header,
            "",
            install_code,
            "",
            library_code,
            "",
            r_body,
        ]
        full_code = "\n".join(p for p in full_parts if p is not None)

        # ── 5.  Collect warnings ───────────────────────────────────────────────
        self._collect_warnings(parse_result, warnings)

        # ── 6.  Build translation notes ────────────────────────────────────────
        translation_notes += [
            f"Problem domain : {intent_result.problem_domain.replace('_', ' ').title()}",
            f"Primary goal   : {intent_result.primary_goal.replace('_', ' ').title()}",
            f"Complexity     : {intent_result.complexity_assessment}",
            f"Packages used  : {', '.join(package_rec.all_packages) or 'base R only'}",
            f"Flow steps     : {flow_result.total_steps}",
            f"Lines of R code: {len(full_code.splitlines())}",
        ]

        return TranslationResult(
            r_code             = full_code,
            r_code_body        = r_body,
            install_code       = install_code,
            library_code       = library_code,
            annotations        = [intent_result.problem_statement],
            warnings           = warnings,
            translation_notes  = translation_notes,
            packages_used      = package_rec.all_packages,
            lines_of_code      = len(full_code.splitlines()),
        )

    # ── AST-based generation ───────────────────────────────────────────────────

    def _ast_generate(self, pr: ParseResult, warnings: List[str]) -> str:
        try:
            from app.services.r_generator import RCodeGenerator
            gen = RCodeGenerator()
            return gen.generate(pr.ast, pr.inline_data, hash_objects=pr.hash_objects)
        except Exception as exc:
            warnings.append(f"AST generator encountered an issue: {exc}. Using fallback.")
            return self._fallback(pr)

    # ── post-processing ────────────────────────────────────────────────────────

    def _post_process(
        self,
        code: str,
        pr: ParseResult,
        pkg_rec: PackageRecommendation,
    ) -> str:
        """
        Light post-processing to make the generated code consistent with the
        recommended packages and style.
        """
        # Nothing to do if code is empty
        if not code.strip():
            return self._fallback(pr)

        # Ensure library calls already at the top of the body are removed
        # (we consolidate them into the preamble)
        body_lines = []
        for line in code.splitlines():
            stripped = line.strip()
            # Remove any library() or require() lines — they go in the preamble
            if re.match(r"^(library|require)\s*\(", stripped):
                continue
            body_lines.append(line)
        return "\n".join(body_lines)

    # ── header ─────────────────────────────────────────────────────────────────

    def _header(
        self,
        ir: IntentResult,
        fr: FlowResult,
        pr_rec: PackageRecommendation,
    ) -> str:
        pkgs = ", ".join(pr_rec.all_packages) or "base R"
        lines = [
            "# ===============================================================",
            "# AUTO-GENERATED R CODE -- SAS -> R Translation Module",
            "# ===============================================================",
            f"# Domain      : {ir.problem_domain.replace('_', ' ').title()}",
            f"# Goal        : {ir.primary_goal.replace('_', ' ').title()}",
            f"# Complexity  : {ir.complexity_assessment}",
            f"# Packages    : {pkgs}",
            f"# Flow steps  : {fr.total_steps}",
            "#",
        ]

        # Problem statement (word-wrapped at ~70 chars)
        stmt = ir.problem_statement
        lines.append("# Problem statement:")
        while len(stmt) > 70:
            split_at = stmt[:70].rfind(" ")
            if split_at == -1:
                split_at = 70
            lines.append(f"#   {stmt[:split_at]}")
            stmt = stmt[split_at:].lstrip()
        if stmt:
            lines.append(f"#   {stmt}")
        lines.append("#")

        # Execution flow summary
        if fr.steps:
            lines.append("# Execution flow:")
            for step in fr.steps:
                lines.append(f"#   {step.order}. {step.name}")
        lines.append("# ═══════════════════════════════════════════════════════════════")
        return "\n".join(lines)

    # ── warnings ───────────────────────────────────────────────────────────────

    def _collect_warnings(self, pr: ParseResult, warnings: List[str]) -> None:
        if pr.has_macros:
            warnings.append(
                "SAS macro variables detected — macro logic has been expanded or simplified. "
                "Verify that all &variable references are resolved correctly."
            )
        if pr.has_sql:
            warnings.append(
                "PROC SQL translated as dplyr joins / filters. "
                "Verify complex subquery or CREATE TABLE logic manually."
            )
        if pr.has_proc_mixed:
            warnings.append(
                "PROC MIXED translated using nlme::lme(). "
                "Verify model specification (random=, correlation=) and covariance structure."
            )
        if pr.has_clinical_procs:
            warnings.append(
                "Clinical statistical procedures (PHREG / LIFETEST / LOGISTIC / MIXED) detected. "
                "Validate model specification and output formatting against protocol requirements."
            )
        if pr.has_retain:
            warnings.append(
                "RETAIN statement translated using dplyr cumulative functions (cumsum, lag). "
                "Verify running totals and carry-forward logic."
            )
        if pr.has_array:
            warnings.append(
                "ARRAY processing translated using R apply functions. "
                "Verify array dimensions, indexing, and loop bounds."
            )
        if any(n.get("type") == "proc_fcmp" for n in pr.ast):
            warnings.append(
                "PROC FCMP custom functions detected — no direct R equivalent. "
                "Manual conversion of custom SAS functions required."
            )
        unknown = [n.get("statement", "") for n in pr.ast if n.get("type") == "unknown"]
        if unknown:
            warnings.append(
                f"{len(unknown)} SAS statement(s) could not be fully translated "
                "and are marked with # TODO comments in the R code."
            )

    # ── fallback generator ────────────────────────────────────────────────────

    def _fallback(self, pr: ParseResult) -> str:
        """Minimal skeleton when the AST generator fails."""
        lines = [
            f"# ── Fallback translation for {pr.proc_types or ['SAS']} code ──",
            "",
        ]

        if pr.data_steps:
            ds_name = pr.data_steps[0].get("dataset", "df")
            lines.append(f"# Create dataset")
            col_defs = []
            for var, vtype in list(pr.variables.items())[:8]:
                col_defs.append(
                    f"  {var} = character(0)" if vtype == "character"
                    else f"  {var} = numeric(0)"
                )
            lines.append(f"{ds_name} <- data.frame(")
            lines.append(",\n".join(col_defs) if col_defs else "  # columns here")
            lines.append(")")
            lines.append("")

        for proc in pr.proc_steps:
            pt = proc["proc_type"]
            ds = proc.get("input_dataset", "df")
            lines.append(f"# ── PROC {pt.upper()} equivalent ──────────────────────────")

            if pt == "means":
                avars = ", ".join(str(v) for v in proc.get("variables", ["value"])[:4])
                cls   = ", ".join(str(v) for v in proc.get("class_vars", [])[:2])
                if cls:
                    lines.append(f"summary_stats <- {ds} %>%")
                    lines.append(f"  group_by({cls}) %>%")
                    lines.append(f"  summarise(across(c({avars}), list(N=~sum(!is.na(.)), Mean=mean, SD=sd, Min=min, Max=max), na.rm=TRUE))")
                else:
                    lines.append(f"summary_stats <- {ds} %>%")
                    lines.append(f"  summarise(across(c({avars or 'everything()'}), list(N=~sum(!is.na(.)), Mean=mean, SD=sd), na.rm=TRUE))")
                lines.append(f"print(summary_stats)")

            elif pt == "freq":
                var = str(proc.get("variables", ["category"])[0]) if proc.get("variables") else "category"
                lines.append(f"freq_table <- {ds} %>%")
                lines.append(f"  count({var}) %>%")
                lines.append(f"  mutate(pct = n / sum(n) * 100)")
                lines.append(f"print(freq_table)")

            elif pt == "sort":
                by_vars = ", ".join(str(v) for v in proc.get("by_vars", ["id"])[:3])
                lines.append(f"{ds} <- {ds} %>% arrange({by_vars})")

            elif pt == "print":
                lines.append(f"print({ds})")

            elif pt == "reg":
                lines.append(f"model <- lm(response ~ ., data = {ds})")
                lines.append(f"summary(model)")

            elif pt == "glm":
                lines.append(f"model <- aov(response ~ group, data = {ds})")
                lines.append(f"summary(model)")

            elif pt == "logistic":
                lines.append(f"model <- glm(outcome ~ ., data = {ds}, family = binomial)")
                lines.append(f"summary(model)")
                lines.append(f"exp(coef(model))  # odds ratios")

            elif pt in ("phreg",):
                lines.append(f"library(survival)")
                lines.append(f"model <- coxph(Surv(time, event) ~ ., data = {ds})")
                lines.append(f"summary(model)")

            elif pt == "lifetest":
                lines.append(f"library(survival)")
                lines.append(f"km_fit <- survfit(Surv(time, event) ~ group, data = {ds})")
                lines.append(f"summary(km_fit)")
                lines.append(f"survdiff(Surv(time, event) ~ group, data = {ds})  # log-rank")

            elif pt == "export":
                lines.append(f"write.csv({ds}, file = 'output.csv', row.names = FALSE)")

            elif pt == "transpose":
                lines.append(f"library(tidyr)")
                lines.append(f"wide_data <- {ds} %>% pivot_wider(names_from = variable, values_from = value)")

            else:
                lines.append(f"# TODO: Translate PROC {pt.upper()} logic")

            lines.append("")

        return "\n".join(lines)
