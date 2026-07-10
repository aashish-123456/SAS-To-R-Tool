"""
Translation Pipeline — Orchestrator
Runs all six translation engines in sequence and returns a unified result
that the API can serialise directly into JSON.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional

from .parser_engine            import ParserEngine,              ParseResult
from .intent_engine            import IntentEngine,              IntentResult
from .execution_flow_engine    import ExecutionFlowEngine,       FlowResult
from .package_recommender_engine import PackageRecommenderEngine, PackageRecommendation
from .translation_engine       import TranslationEngine,         TranslationResult
from .validation_engine        import ExecutionFlowValidationEngine, FlowValidationResult
from .lineage_engine           import LineageEngine,             LineageResult


# ─────────────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    parse:       ParseResult
    intent:      IntentResult
    flow:        FlowResult
    packages:    PackageRecommendation
    translation: TranslationResult
    validation:  FlowValidationResult
    lineage:     LineageResult = field(default_factory=lambda: LineageResult({}, [], {}, '', ''))

    # ── serialisation ──────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        pr  = self.parse
        ir  = self.intent
        fr  = self.flow
        pkr = self.packages
        tr  = self.translation
        vr  = self.validation

        return {
            # ── Engine 1: Parser ──────────────────────────────────────────────
            "parse": {
                "proc_types":       pr.proc_types,
                "functions":        sorted(pr.functions),
                "keywords":         sorted(pr.keywords),
                "operators":        sorted(pr.operators),
                "variables":        pr.variables,
                "datasets":         pr.datasets,
                "total_statements": pr.total_statements,
                "data_steps_count": len(pr.data_steps),
                "proc_steps_count": len(pr.proc_steps),
                "if_else_count":    len(pr.if_else_chains),
                "do_loop_count":    len(pr.do_loops),
                "macros_count":     len(pr.macros),
                "has_macros":       pr.has_macros,
                "has_sql":          pr.has_sql,
                "has_merge":        pr.has_merge,
                "has_array":        pr.has_array,
                "has_retain":       pr.has_retain,
                "has_clinical":     pr.has_clinical_procs,
                "statistics_found": sorted(pr.statistics_requested),
            },

            # ── Engine 2: Intent ──────────────────────────────────────────────
            "intent": {
                "problem_domain":     ir.problem_domain,
                "domain_confidence":  round(ir.domain_confidence, 2),
                "primary_goal":       ir.primary_goal,
                "secondary_goals":    ir.secondary_goals,
                "problem_statement":  ir.problem_statement,
                "methodology":        ir.methodology,
                "expected_outputs":   ir.expected_outputs,
                "analysis_types":     ir.analysis_types,
                "complexity":         ir.complexity_assessment,
                "key_metrics":        ir.key_metrics,
                "transformations":    ir.data_transformations,
                "classification_rules": ir.classification_logic,
                "output_segments": [
                    {
                        "name":       s.name,
                        "description":s.description,
                        "proc_type":  s.proc_type,
                        "variables":  s.variables_involved,
                    }
                    for s in ir.output_segments
                ],
            },

            # ── Engine 3: Execution Flow ───────────────────────────────────────
            "flow": {
                "total_steps":     fr.total_steps,
                "flow_description":fr.flow_description,
                "input_datasets":  fr.input_datasets,
                "output_datasets": fr.output_datasets,
                "critical_path":   fr.critical_path,
                "data_lineage":    fr.data_lineage,
                "steps": [
                    {
                        "order":          s.order,
                        "name":           s.name,
                        "description":    s.description,
                        "step_type":      s.step_type,
                        "sas_constructs": s.sas_constructs,
                        "inputs":         s.inputs,
                        "outputs":        s.outputs,
                        "dependencies":   s.dependencies,
                    }
                    for s in fr.steps
                ],
            },

            # ── Engine 4: Package Recommender ──────────────────────────────────
            "packages": {
                "all_packages":       pkr.all_packages,
                "install_code":       pkr.install_code,
                "library_code":       pkr.library_code,
                "selection_rationale":pkr.selection_rationale,
                "alternatives":       pkr.alternatives,
                "function_mappings": [
                    {
                        "sas_function": fm.sas_function,
                        "r_function":   fm.r_function,
                        "package":      fm.package,
                        "note":         fm.note,
                    }
                    for fm in getattr(pkr, "function_mappings", [])
                ],
                "detection_layers": getattr(pkr, "detection_layers", {}),
                "primary_packages": [
                    {
                        "name":                 p.name,
                        "purpose":              p.purpose,
                        "functions_used":       p.functions_used,
                        "sas_functions_covered":p.sas_functions_covered,
                        "rationale":            p.rationale,
                        "alternatives":         p.alternatives,
                        "complexity_score":     p.complexity_score,
                    }
                    for p in pkr.primary_packages
                ],
            },

            # ── Engine 1.5: Dataset Lineage ───────────────────────────────────
            "lineage": {
                "nodes": {
                    name: {
                        "node_type":   nd.node_type,
                        "library":     nd.library,
                        "full_name":   nd.full_name,
                        "created_by":  nd.created_by,
                        "operations":  nd.operations,
                    }
                    for name, nd in self.lineage.nodes.items()
                },
                "edges": [
                    {
                        "source":     e.source,
                        "target":     e.target,
                        "operation":  e.operation,
                        "join_type":  e.join_type,
                        "by_vars":    e.by_vars,
                    }
                    for e in self.lineage.edges
                ],
                "lineage_map": self.lineage.lineage_map,
                "summary":     self.lineage.summary,
                "mermaid":     self.lineage.mermaid,
            },

            # ── Engine 5: Translation ─────────────────────────────────────────
            "translation": {
                "r_code":           tr.r_code,
                "r_code_preview":   tr.r_code[:900],
                "install_code":     tr.install_code,
                "library_code":     tr.library_code,
                "warnings":         tr.warnings,
                "translation_notes":tr.translation_notes,
                "packages_used":    tr.packages_used,
                "lines_of_code":    tr.lines_of_code,
                "annotations":      tr.annotations,
            },

            # ── Engine 6: Validation ──────────────────────────────────────────
            "validation": {
                "problem_statement_match":   vr.problem_statement_match,
                "execution_flow_match":      vr.execution_flow_match,
                "packages_appropriate":      vr.packages_appropriate,
                "code_complexity":           vr.code_complexity,
                "lines_of_code":             vr.lines_of_code,
                "estimated_equivalence_pct": round(vr.estimated_equivalence_pct, 1),
                "approval_status":           vr.approval_status,
                "validation_summary":        vr.validation_summary,
                "engine_coverage":           vr.engine_coverage,
                "strengths":                 vr.strengths,
                "recommendations":           vr.recommendations,
                "issues": [
                    {
                        "severity":   i.severity,
                        "title":      i.title,
                        "detail":     i.detail,
                        "suggestion": i.suggestion,
                    }
                    for i in vr.issues
                ],
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TranslationPipeline:
    """
    Orchestrates the six-engine Translation Module in sequence.

    Usage::

        from app.translation import TranslationPipeline
        pipeline = TranslationPipeline()
        result = pipeline.run(sas_code, expand_macros_fn=my_macro_expander)
        data = result.to_dict()  # JSON-serialisable
    """

    def __init__(self) -> None:
        self._parser      = ParserEngine()
        self._lineage     = LineageEngine()
        self._intent      = IntentEngine()
        self._flow        = ExecutionFlowEngine()
        self._recommender = PackageRecommenderEngine()
        self._translator  = TranslationEngine()
        self._validator   = ExecutionFlowValidationEngine()

    def run(
        self,
        sas_code: str,
        expand_macros_fn: Optional[Callable[[str], str]] = None,
    ) -> PipelineResult:
        """
        Execute all six engines and return the unified PipelineResult.

        Parameters
        ----------
        sas_code : str
            Raw SAS source code.
        expand_macros_fn : callable, optional
            A function that pre-processes macro expansion before parsing.
            Pass the existing ``_expand_simple_macros`` from main.py.
        """
        # Pre-process
        processed = expand_macros_fn(sas_code) if expand_macros_fn else sas_code

        # Engine 1 — Parse
        parse_result = self._parser.parse(processed)

        # Engine 1.5 — Dataset Lineage
        lineage_result = self._lineage.build(parse_result)

        # Engine 2
        intent_result = self._intent.analyze(parse_result)

        # Engine 3
        flow_result = self._flow.map_flow(parse_result, intent_result)

        # Engine 4
        package_result = self._recommender.recommend(parse_result, intent_result, flow_result)

        # Engine 5
        translation_result = self._translator.translate(
            parse_result, intent_result, flow_result, package_result
        )

        # Engine 6
        validation_result = self._validator.validate(
            parse_result, intent_result, flow_result, package_result, translation_result
        )

        return PipelineResult(
            parse       = parse_result,
            intent      = intent_result,
            flow        = flow_result,
            packages    = package_result,
            translation = translation_result,
            validation  = validation_result,
            lineage     = lineage_result,
        )
