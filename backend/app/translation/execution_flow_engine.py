"""
Engine 3 — Execution Flow Engine
Answers: IN WHAT ORDER does the SAS code execute?
Builds an ordered list of logical steps and maps data lineage.
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

from .parser_engine import ParseResult
from .intent_engine import IntentResult


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FlowStep:
    order: int
    name: str
    description: str
    sas_constructs: List[str]
    inputs: List[str]
    outputs: List[str]
    step_type: str          # data_prep | transform | analysis | output | export
    dependencies: List[int] # order indices of steps this step depends on


@dataclass
class FlowResult:
    steps: List[FlowStep]
    data_lineage: Dict[str, List[str]]  # dataset → [lineage notes]
    critical_path: List[int]            # step order values on critical path
    flow_description: str
    input_datasets: List[str]
    output_datasets: List[str]
    total_steps: int


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class ExecutionFlowEngine:
    """
    Third sub-layer of the Translation Module.
    Maps the exact sequence of operations in the SAS program so the
    Translation Engine can reproduce the same logical flow in R.
    """

    def map_flow(self, pr: ParseResult, ir: IntentResult) -> FlowResult:
        steps = self._build_steps(pr, ir)
        lineage = self._build_lineage(pr)
        critical = self._critical_path(steps)
        description = self._narrate(steps, pr, ir)

        input_ds  = [ds for ds, role in pr.datasets.items() if role in ("input",  "both")]
        output_ds = [ds for ds, role in pr.datasets.items() if role in ("output", "both")]

        return FlowResult(
            steps            = steps,
            data_lineage     = lineage,
            critical_path    = critical,
            flow_description = description,
            input_datasets   = input_ds,
            output_datasets  = output_ds,
            total_steps      = len(steps),
        )

    # ── step builder ───────────────────────────────────────────────────────────

    def _build_steps(self, pr: ParseResult, ir: IntentResult) -> List[FlowStep]:
        steps: List[FlowStep] = []
        order = 1

        # ── 1.  Dataset ingestion / creation ──────────────────────────────────
        for ds_info in pr.data_steps:
            ds_name = ds_info.get("dataset", "dataset")
            sources = ds_info.get("sources", [])
            if sources:
                step = FlowStep(
                    order          = order,
                    name           = f"Load {ds_name}",
                    description    = f"Read dataset '{ds_name}' from {', '.join(sources)}",
                    sas_constructs = ["DATA step", "SET"],
                    inputs         = sources,
                    outputs        = [ds_name],
                    step_type      = "data_prep",
                    dependencies   = [],
                )
            else:
                step = FlowStep(
                    order          = order,
                    name           = f"Create {ds_name}",
                    description    = (
                        f"Create dataset '{ds_name}' with inline DATALINES / CARDS data"
                    ),
                    sas_constructs = ["DATA step", "INPUT", "DATALINES"],
                    inputs         = [],
                    outputs        = [ds_name],
                    step_type      = "data_prep",
                    dependencies   = [],
                )
            steps.append(step)
            order += 1

        prep_orders = [s.order for s in steps if s.step_type == "data_prep"]

        # ── 2.  Conditional classification / derivation ───────────────────────
        if pr.if_else_chains:
            derived_vars = list(set(
                re.findall(r"\b([A-Za-z_]\w*)\s*=", str(pr.if_else_chains))
            ))[:4]
            ds_in = [s.outputs[0] for s in steps if s.step_type == "data_prep"] or ["dataset"]
            steps.append(FlowStep(
                order          = order,
                name           = "Apply Classification / Derivation Rules",
                description    = (
                    f"Apply {len(pr.if_else_chains)} IF-THEN-ELSE rule(s) to classify "
                    f"or derive variable(s): {', '.join(derived_vars[:3]) or 'new variables'}"
                ),
                sas_constructs = ["IF-THEN-ELSE", "Assignment"],
                inputs         = ds_in,
                outputs        = ds_in,
                step_type      = "transform",
                dependencies   = prep_orders,
            ))
            order += 1

        # ── 3.  DO-loop processing ────────────────────────────────────────────
        if pr.do_loops:
            steps.append(FlowStep(
                order          = order,
                name           = f"Iterative Processing ({len(pr.do_loops)} DO loop(s))",
                description    = "Execute DO loop(s) to process repeated or array-based operations",
                sas_constructs = ["DO loop", "END"],
                inputs         = [s.outputs[0] for s in steps if s.outputs] or ["dataset"],
                outputs        = ["loop_result"],
                step_type      = "transform",
                dependencies   = [s.order for s in steps],
            ))
            order += 1

        # ── 4.  MERGE / JOIN ──────────────────────────────────────────────────
        if pr.has_merge:
            all_ds = list(pr.datasets.keys())[:3]
            steps.append(FlowStep(
                order          = order,
                name           = "Merge Datasets",
                description    = "Combine multiple datasets by a common key variable (MERGE … BY)",
                sas_constructs = ["DATA step", "MERGE", "BY"],
                inputs         = all_ds,
                outputs        = ["merged_data"],
                step_type      = "transform",
                dependencies   = prep_orders,
            ))
            order += 1

        # ── 5.  PROC SQL ──────────────────────────────────────────────────────
        for proc in [p for p in pr.proc_steps if p["proc_type"] == "sql"]:
            steps.append(FlowStep(
                order          = order,
                name           = "SQL Query / Join",
                description    = (
                    "Execute SQL-style query via PROC SQL (joins, aggregations, filters, "
                    "or CREATE TABLE)"
                ),
                sas_constructs = ["PROC SQL", "SELECT", "FROM", "WHERE", "JOIN"],
                inputs         = [proc.get("input_dataset", "dataset")],
                outputs        = [proc.get("output_dataset") or "sql_result"],
                step_type      = "transform",
                dependencies   = [s.order for s in steps if s.step_type in ("data_prep", "transform")],
            ))
            order += 1

        transform_orders = [s.order for s in steps if s.step_type in ("data_prep", "transform")]

        # ── 6.  Sorting (required before BY-group PROCs) ──────────────────────
        for proc in [p for p in pr.proc_steps if p["proc_type"] == "sort"]:
            by_vars = proc.get("by_vars", [])
            in_ds = proc.get("input_dataset") or (steps[-1].outputs[0] if steps else "dataset")
            out_ds = proc.get("output_dataset") or in_ds
            steps.append(FlowStep(
                order          = order,
                name           = "Sort Data",
                description    = (
                    f"Sort dataset by {', '.join(str(v) for v in by_vars) or 'specified variable(s)'} "
                    "using PROC SORT"
                ),
                sas_constructs = ["PROC SORT", "BY"],
                inputs         = [in_ds],
                outputs        = [out_ds],
                step_type      = "transform",
                dependencies   = transform_orders,
            ))
            order += 1

        analysis_deps = [s.order for s in steps if s.step_type in ("data_prep", "transform")]

        # ── 7.  PROC MEANS ────────────────────────────────────────────────────
        for proc in [p for p in pr.proc_steps if p["proc_type"] == "means"]:
            cls   = proc.get("class_vars", [])
            avars = proc.get("variables", [])
            stats = list(pr.statistics_requested) or ["N", "Mean", "Std", "Min", "Max"]
            steps.append(FlowStep(
                order          = order,
                name           = "Compute Descriptive Statistics",
                description    = (
                    f"Calculate {', '.join(str(s) for s in stats[:5])} "
                    f"for {', '.join(str(v) for v in avars[:3]) or 'numeric variables'}"
                    + (f" grouped by {', '.join(str(v) for v in cls[:3])}" if cls else "")
                ),
                sas_constructs = ["PROC MEANS", "VAR", "CLASS", "BY"],
                inputs         = [proc.get("input_dataset") or "dataset"],
                outputs        = [proc.get("output_dataset") or "summary_stats"],
                step_type      = "analysis",
                dependencies   = analysis_deps,
            ))
            order += 1

        # ── 8.  PROC FREQ ─────────────────────────────────────────────────────
        for proc in [p for p in pr.proc_steps if p["proc_type"] == "freq"]:
            avars = proc.get("variables", ["categorical_variable"])
            steps.append(FlowStep(
                order          = order,
                name           = "Compute Frequency Tables",
                description    = (
                    f"Generate frequency counts and percentages for "
                    f"{', '.join(str(v) for v in avars[:3])}"
                ),
                sas_constructs = ["PROC FREQ", "TABLES"],
                inputs         = [proc.get("input_dataset") or "dataset"],
                outputs        = ["frequency_table"],
                step_type      = "analysis",
                dependencies   = analysis_deps,
            ))
            order += 1

        # ── 9.  Regression / GLM / Logistic / Mixed ───────────────────────────
        _model_labels = {
            "reg":      "Linear Regression (PROC REG)",
            "glm":      "ANOVA / GLM (PROC GLM)",
            "logistic": "Logistic Regression (PROC LOGISTIC)",
            "mixed":    "Mixed Model (PROC MIXED)",
        }
        for proc in [p for p in pr.proc_steps if p["proc_type"] in _model_labels]:
            steps.append(FlowStep(
                order          = order,
                name           = f"Fit {_model_labels[proc['proc_type']]}",
                description    = (
                    f"Fit statistical model — {_model_labels[proc['proc_type']]}"
                ),
                sas_constructs = [f"PROC {proc['proc_type'].upper()}", "MODEL"],
                inputs         = [proc.get("input_dataset") or "dataset"],
                outputs        = ["model_output"],
                step_type      = "analysis",
                dependencies   = analysis_deps,
            ))
            order += 1

        # ── 10.  Survival Analysis ────────────────────────────────────────────
        for proc in [p for p in pr.proc_steps if p["proc_type"] in ("phreg", "lifetest")]:
            steps.append(FlowStep(
                order          = order,
                name           = "Survival Analysis",
                description    = "Perform time-to-event analysis (Kaplan-Meier / Cox PH)",
                sas_constructs = [f"PROC {proc['proc_type'].upper()}", "TIME", "MODEL"],
                inputs         = [proc.get("input_dataset") or "dataset"],
                outputs        = ["survival_output"],
                step_type      = "analysis",
                dependencies   = analysis_deps,
            ))
            order += 1

        # ── 11.  PROC PRINT ───────────────────────────────────────────────────
        print_procs = [p for p in pr.proc_steps if p["proc_type"] == "print"]
        if print_procs:
            steps.append(FlowStep(
                order          = order,
                name           = "Display Results",
                description    = "Format and display data / results using PROC PRINT",
                sas_constructs = ["PROC PRINT"],
                inputs         = [print_procs[0].get("input_dataset") or "dataset"],
                outputs        = ["printed_output"],
                step_type      = "output",
                dependencies   = [s.order for s in steps],
            ))
            order += 1

        # ── 12.  Export ───────────────────────────────────────────────────────
        for proc in [p for p in pr.proc_steps if p["proc_type"] == "export"]:
            steps.append(FlowStep(
                order          = order,
                name           = "Export Results",
                description    = "Export processed data to external file (CSV / Excel)",
                sas_constructs = ["PROC EXPORT"],
                inputs         = [proc.get("input_dataset") or "dataset"],
                outputs        = ["exported_file"],
                step_type      = "export",
                dependencies   = [s.order for s in steps],
            ))
            order += 1

        # ── fallback if nothing was built ─────────────────────────────────────
        if not steps:
            steps.append(FlowStep(
                order          = 1,
                name           = "Process Data",
                description    = "Execute SAS program to process and analyze data",
                sas_constructs = ["DATA step", "PROC steps"],
                inputs         = list(pr.datasets.keys())[:2],
                outputs        = list(pr.datasets.keys())[-1:] or ["output"],
                step_type      = "transform",
                dependencies   = [],
            ))
        return steps

    # ── lineage ────────────────────────────────────────────────────────────────

    def _build_lineage(self, pr: ParseResult) -> Dict[str, List[str]]:
        lineage: Dict[str, List[str]] = {}
        for ds, role in pr.datasets.items():
            notes: List[str] = []
            if role == "output":
                notes.append("Created by DATA step or PROC OUT=")
            elif role == "input":
                notes.append("Used as source input")
            else:
                notes.append("Created and subsequently used within the program")
            lineage[ds] = notes
        return lineage

    # ── critical path ──────────────────────────────────────────────────────────

    def _critical_path(self, steps: List[FlowStep]) -> List[int]:
        if not steps:
            return []
        critical = [
            s.order for s in steps
            if s.step_type in ("data_prep", "analysis", "output", "export")
        ]
        return critical or [s.order for s in steps]

    # ── narrative ──────────────────────────────────────────────────────────────

    def _narrate(self, steps: List[FlowStep], pr: ParseResult, ir: IntentResult) -> str:
        if not steps:
            return "The program executes sequentially with no distinct steps identified."
        domain = ir.problem_domain.replace("_", " ").title()
        parts = [
            f"The {domain} program executes in {len(steps)} logical step(s):"
        ]
        for s in steps:
            parts.append(f"  {s.order}. [{s.step_type.upper()}] {s.name} — {s.description}")
        if pr.datasets:
            in_ds  = [ds for ds, r in pr.datasets.items() if r in ("input",  "both")]
            out_ds = [ds for ds, r in pr.datasets.items() if r in ("output", "both")]
            if in_ds:
                parts.append(f"\nInput datasets:  {', '.join(in_ds)}")
            if out_ds:
                parts.append(f"Output datasets: {', '.join(out_ds)}")
        return "\n".join(parts)
