"""
AI Dependency Intelligence Engine - Phase 1 & 2
Complete semantic dependency analysis with lineage graph, AST, and intelligent classification
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
from pathlib import Path


# ============================================================================
# PHASE 1: LINEAGE GRAPH DATA STRUCTURES
# ============================================================================

class DatasetState(Enum):
    EXTERNAL_INPUT = "external_input"
    GENERATED = "generated"
    REFERENCED = "referenced"
    QC_ONLY = "qc_only"
    INTERMEDIATE = "intermediate"


class DatasetRole(Enum):
    DEMOGRAPHICS = "demographics"
    ADVERSE_EVENTS = "adverse_events"
    VISIT_DATA = "visit_data"
    ANALYSIS_DATASET = "analysis_dataset"
    QC_REFERENCE = "qc_reference"
    TEMPORARY = "temporary"
    UNKNOWN = "unknown"


class StepType(Enum):
    DATA_STEP = "data_step"
    PROC_SORT = "proc_sort"
    PROC_MEANS = "proc_means"
    PROC_SQL = "proc_sql"
    PROC_REPORT = "proc_report"
    PROC_COMPARE = "proc_compare"
    PROC_IMPORT = "proc_import"
    PROC_OTHER = "proc_other"


@dataclass
class Step:
    step_id: str
    step_type: StepType
    name: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    line_range: Tuple[int, int] = (0, 0)
    variables_used: Dict[str, List[str]] = field(default_factory=dict)
    variables_output: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.step_id)


@dataclass
class Dataset:
    name: str
    state: DatasetState
    producer: Optional[Step] = None
    consumers: List[Step] = field(default_factory=list)
    created_at_line: Optional[int] = None
    first_used_at_line: Optional[int] = None
    required_variables: List[str] = field(default_factory=list)
    role: DatasetRole = DatasetRole.UNKNOWN
    confidence: float = 0.5
    is_workflow_dependency: bool = False
    is_qc_only: bool = False
    library: str = "work"  # e.g., "raw", "sdtm", "adam"


@dataclass
class LineageGraph:
    datasets: Dict[str, Dataset] = field(default_factory=dict)
    steps: List[Step] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    external_inputs: List[str] = field(default_factory=list)
    generated_outputs: List[str] = field(default_factory=list)
    workflow_dependencies: List[str] = field(default_factory=list)
    qc_datasets: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'datasets': {k: {
                'name': v.name,
                'state': v.state.value,
                'role': v.role.value,
                'producer': v.producer.name if v.producer else None,
                'consumers': [c.name for c in v.consumers],
                'required_variables': v.required_variables,
                'is_workflow_dependency': v.is_workflow_dependency,
                'is_qc_only': v.is_qc_only
            } for k, v in self.datasets.items()},
            'steps': [
                {
                    'id': s.step_id,
                    'type': s.step_type.value,
                    'name': s.name,
                    'inputs': s.inputs,
                    'outputs': s.outputs
                }
                for s in self.steps
            ],
            'execution_order': self.execution_order,
            'external_inputs': self.external_inputs,
            'generated_outputs': self.generated_outputs,
            'workflow_dependencies': self.workflow_dependencies,
            'qc_datasets': self.qc_datasets
        }


# ============================================================================
# PHASE 1: LINEAGE BUILDER
# ============================================================================

class LineageBuilder:
    """Build dataset lineage graph from SAS code"""

    def __init__(self):
        self.datasets: Dict[str, Dataset] = {}
        self.steps: List[Step] = []
        self.step_counter = 0

    def build(self, sas_code: str) -> LineageGraph:
        """Build complete lineage graph"""

        # Step 1: Extract steps
        self._extract_steps(sas_code)

        # Step 2: Classify datasets
        self._classify_datasets(sas_code)

        # Step 3: Build execution order
        execution_order = self._build_execution_order()

        # Step 4: Identify workflow dependencies
        workflow_deps = self._identify_workflow_dependencies(execution_order)

        # Step 5: Build graph
        graph = LineageGraph(
            datasets=self.datasets,
            steps=self.steps,
            external_inputs=self._find_external_inputs(),
            generated_outputs=self._find_generated_outputs(),
            workflow_dependencies=workflow_deps,
            qc_datasets=self._find_qc_datasets(),
            execution_order=execution_order
        )

        return graph

    def _extract_steps(self, code: str):
        """Extract all DATA and PROC steps"""
        lines = code.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # DATA Step
            if re.match(r'^\s*data\s+', line, re.IGNORECASE):
                step = self._parse_data_step(lines, i)
                if step:
                    self.steps.append(step)
                    # Register datasets
                    for ds in step.outputs:
                        if ds not in self.datasets:
                            self.datasets[ds] = Dataset(
                                name=ds,
                                state=DatasetState.GENERATED,
                                created_at_line=i,
                                producer=step
                            )
                    for ds in step.inputs:
                        if ds not in self.datasets:
                            self.datasets[ds] = Dataset(
                                name=ds,
                                state=DatasetState.EXTERNAL_INPUT,
                                first_used_at_line=i
                            )

            # PROC Step
            elif re.match(r'^\s*proc\s+', line, re.IGNORECASE):
                step = self._parse_proc_step(lines, i)
                if step:
                    self.steps.append(step)
                    # Register datasets
                    for ds in step.outputs:
                        if ds not in self.datasets:
                            self.datasets[ds] = Dataset(
                                name=ds,
                                state=DatasetState.GENERATED,
                                created_at_line=i,
                                producer=step
                            )
                    for ds in step.inputs:
                        if ds not in self.datasets:
                            self.datasets[ds] = Dataset(
                                name=ds,
                                state=DatasetState.EXTERNAL_INPUT,
                                first_used_at_line=i
                            )
                        else:
                            self.datasets[ds].consumers.append(step)
                            if not self.datasets[ds].first_used_at_line:
                                self.datasets[ds].first_used_at_line = i

            i += 1

    def _parse_data_step(self, lines: List[str], start_line: int) -> Optional[Step]:
        """Parse DATA step"""
        step_id = f"step_{self.step_counter}"
        self.step_counter += 1

        code_block = self._extract_block(lines, start_line)

        # Extract output dataset
        output_match = re.search(r'data\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)', code_block, re.IGNORECASE)
        if not output_match:
            return None

        outputs = [output_match.group(1).lower()]

        # Extract input datasets
        inputs = []
        for pattern in [
            r'set\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)',
            r'merge\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)',
            r'update\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)',
            r'modify\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)'
        ]:
            for match in re.finditer(pattern, code_block, re.IGNORECASE):
                inputs.append(match.group(1).lower())

        # Extract variables
        var_matches = re.findall(r'var\s+([a-zA-Z_]\w*(?:\s+[a-zA-Z_]\w*)*)', code_block, re.IGNORECASE)
        variables_output = []
        for match in var_matches:
            variables_output.extend(match.split())

        return Step(
            step_id=step_id,
            step_type=StepType.DATA_STEP,
            name=f"data {outputs[0]}",
            inputs=list(set(inputs)),
            outputs=outputs,
            line_range=(start_line, start_line + len(code_block.split('\n'))),
            variables_output=variables_output
        )

    def _parse_proc_step(self, lines: List[str], start_line: int) -> Optional[Step]:
        """Parse PROC step"""
        step_id = f"step_{self.step_counter}"
        self.step_counter += 1

        code_block = self._extract_block(lines, start_line)
        first_line = lines[start_line].strip()

        # Identify PROC type
        proc_match = re.search(r'proc\s+(\w+)', first_line, re.IGNORECASE)
        if not proc_match:
            return None

        proc_type = proc_match.group(1).lower()

        # Map to StepType
        step_type_map = {
            'sort': StepType.PROC_SORT,
            'means': StepType.PROC_MEANS,
            'sql': StepType.PROC_SQL,
            'report': StepType.PROC_REPORT,
            'compare': StepType.PROC_COMPARE,
            'import': StepType.PROC_IMPORT,
        }
        step_type = step_type_map.get(proc_type, StepType.PROC_OTHER)

        # Extract inputs and outputs
        inputs = []
        outputs = []

        # data= parameter (input)
        data_match = re.search(r'data\s*=\s*([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)', code_block, re.IGNORECASE)
        if data_match:
            inputs.append(data_match.group(1).lower())

        # out= parameter (output)
        out_match = re.search(r'out\s*=\s*([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)', code_block, re.IGNORECASE)
        if out_match:
            outputs.append(out_match.group(1).lower())

        # PROC SQL create table (output)
        if proc_type == 'sql':
            create_match = re.search(
                r'create\s+table\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)',
                code_block, re.IGNORECASE
            )
            if create_match:
                outputs.append(create_match.group(1).lower())

        # base= and compare= (PROC COMPARE inputs, these are QC datasets)
        for param in ['base', 'compare']:
            param_match = re.search(
                f'{param}\\s*=\\s*([a-zA-Z_]\\w*(?:\\.[a-zA-Z_]\\w*)?)',
                code_block, re.IGNORECASE
            )
            if param_match:
                ds = param_match.group(1).lower()
                if ds not in inputs:
                    inputs.append(ds)

        # Extract variables used
        variables_used = {}
        for input_ds in inputs:
            var_matches = re.findall(r'var\s+([a-zA-Z_]\w*(?:\s+[a-zA-Z_]\w*)*)', code_block, re.IGNORECASE)
            if var_matches:
                variables_used[input_ds] = []
                for match in var_matches:
                    variables_used[input_ds].extend(match.split())

        return Step(
            step_id=step_id,
            step_type=step_type,
            name=f"proc {proc_type}",
            inputs=list(set(inputs)),
            outputs=outputs,
            line_range=(start_line, start_line + len(code_block.split('\n'))),
            variables_used=variables_used
        )

    def _extract_block(self, lines: List[str], start_line: int) -> str:
        """Extract a complete SAS statement block (ends with RUN; or QUIT;)"""
        block = [lines[start_line]]
        i = start_line + 1

        while i < len(lines):
            line = lines[i].strip()
            block.append(lines[i])

            if re.search(r'(run|quit)\s*;', line, re.IGNORECASE):
                break
            i += 1

        return '\n'.join(block)

    def _classify_datasets(self, code: str):
        """Classify datasets by role"""
        code_upper = code.upper()

        for ds_name, ds in self.datasets.items():
            # Infer library
            if '.' in ds_name:
                ds.library = ds_name.split('.')[0]

            # Classify by name pattern
            ds_lower = ds_name.lower()
            if ds.library in ['raw', 'source'] or 'raw' in ds_lower or 'source' in ds_lower:
                ds.role = DatasetRole.DEMOGRAPHICS if 'dem' in ds_lower or 'dm' in ds_lower else DatasetRole.ADVERSE_EVENTS if 'ae' in ds_lower else DatasetRole.UNKNOWN
            elif ds.library in ['sdtm'] or 'sdtm' in ds_lower:
                ds.role = DatasetRole.DEMOGRAPHICS if 'dm' in ds_lower else DatasetRole.ADVERSE_EVENTS if 'ae' in ds_lower else DatasetRole.VISIT_DATA if 'sv' in ds_lower or 'visit' in ds_lower else DatasetRole.UNKNOWN
            elif ds.library in ['adam'] or 'adam' in ds_lower or 'adsl' in ds_lower:
                ds.role = DatasetRole.ANALYSIS_DATASET
            elif 'qc' in ds_lower or 'compare' in ds_lower:
                ds.role = DatasetRole.QC_REFERENCE
                ds.is_qc_only = True
            else:
                # General fallback by keyword
                if 'dm' in ds_lower or 'demographic' in ds_lower:
                    ds.role = DatasetRole.DEMOGRAPHICS
                elif 'ae' in ds_lower or 'adverse' in ds_lower:
                    ds.role = DatasetRole.ADVERSE_EVENTS
                elif 'adsl' in ds_lower:
                    ds.role = DatasetRole.ANALYSIS_DATASET
                else:
                    ds.role = DatasetRole.UNKNOWN

            # Update confidence
            ds.confidence = 0.95 if ds.role != DatasetRole.UNKNOWN else 0.5

    def _build_execution_order(self) -> List[str]:
        """Build execution order using topological sort"""
        order = []
        visited = set()

        def visit(ds_name):
            if ds_name in visited:
                return
            visited.add(ds_name)

            ds = self.datasets.get(ds_name)
            if ds and ds.producer:
                for input_ds in ds.producer.inputs:
                    if input_ds in self.datasets:
                        visit(input_ds)

            order.append(ds_name)

        for ds_name in self.datasets:
            visit(ds_name)

        return order

    def _identify_workflow_dependencies(self, execution_order: List[str]) -> List[str]:
        """Identify datasets that are created and consumed within workflow"""
        deps = []

        for ds_name in execution_order:
            ds = self.datasets[ds_name]

            # Workflow dep: dataset is generated AND consumed within execution
            if ds.state == DatasetState.GENERATED and ds.consumers:
                # Check if consumed step comes after producer step
                if ds.producer:
                    producer_idx = next(
                        (i for i, s in enumerate(self.steps) if s == ds.producer),
                        -1
                    )
                    for consumer in ds.consumers:
                        consumer_idx = next(
                            (i for i, s in enumerate(self.steps) if s == consumer),
                            -1
                        )
                        if consumer_idx > producer_idx:
                            deps.append(ds_name)
                            break

        return deps

    def _find_external_inputs(self) -> List[str]:
        """Find datasets that must be uploaded"""
        return [
            ds_name for ds_name, ds in self.datasets.items()
            if ds.state == DatasetState.EXTERNAL_INPUT or (ds.state == DatasetState.REFERENCED and not ds.producer)
        ]

    def _find_generated_outputs(self) -> List[str]:
        """Find datasets created by code"""
        return [
            ds_name for ds_name, ds in self.datasets.items()
            if ds.state == DatasetState.GENERATED
        ]

    def _find_qc_datasets(self) -> List[str]:
        """Find QC reference datasets"""
        return [
            ds_name for ds_name, ds in self.datasets.items()
            if ds.is_qc_only
        ]


# ============================================================================
# PHASE 1: DEPENDENCY CLASSIFIER
# ============================================================================

class DependencyClassifier:
    """Classify dependencies and determine upload requirements"""

    @staticmethod
    def classify(lineage: LineageGraph) -> Dict:
        """Classify all dependencies"""
        decisions = {}

        for ds_name, ds in lineage.datasets.items():
            decision = {
                'dataset': ds_name,
                'state': ds.state.value,
                'role': ds.role.value,
                'upload_required': False,
                'reason': '',
                'alternatives': [],
                'confidence': ds.confidence
            }

            if ds.state == DatasetState.EXTERNAL_INPUT:
                decision['upload_required'] = True
                decision['reason'] = 'Used by SET/MERGE but never created'

            elif ds.state == DatasetState.GENERATED:
                decision['upload_required'] = False
                decision['reason'] = 'Created by DATA step or PROC SQL'

            elif ds.state == DatasetState.REFERENCED:
                decision['upload_required'] = True
                decision['reason'] = 'Used in PROC but never created'
                # Find similar generated datasets
                decision['alternatives'] = [
                    g for g in lineage.generated_outputs
                    if DependencyClassifier._similar_name(ds_name, g)
                ]

            elif ds.state == DatasetState.QC_ONLY:
                decision['upload_required'] = 'conditional'
                decision['reason'] = 'QC dataset (used in PROC COMPARE)'
                decision['condition'] = 'Upload only if QC validation enabled'

            elif ds.state == DatasetState.INTERMEDIATE:
                decision['upload_required'] = False
                decision['reason'] = 'Intermediate workflow dataset'

            decisions[ds_name] = decision

        return decisions

    @staticmethod
    def _similar_name(name1: str, name2: str) -> bool:
        """Check if names are similar"""
        # Remove library prefix
        base1 = name1.split('.')[-1].lower()
        base2 = name2.split('.')[-1].lower()

        if base1 == base2:
            return True

        # Check if one is substring of other
        if base1 in base2 or base2 in base1:
            return True

        # Levenshtein-like: allow 1-2 char differences
        if abs(len(base1) - len(base2)) <= 2:
            diff = sum(1 for c1, c2 in zip(base1, base2) if c1 != c2)
            if diff <= 2:
                return True

        return False


# ============================================================================
# PHASE 2: SEMANTIC VARIABLE MAPPER
# ============================================================================

class SemanticVariableMapper:
    """Map variables using fuzzy matching and semantic similarity"""

    def __init__(self):
        self.variable_role_patterns = {
            'demographics': ['age', 'sex', 'race', 'weight', 'height', 'dm'],
            'treatment': ['trt', 'dose', 'regimen', 'drug', 'therapy'],
            'outcome': ['efficacy', 'safety', 'aes', 'response', 'event'],
            'timing': ['day', 'visit', 'month', 'date', 'time', 'week']
        }

    def map_dataset_variables(self, uploaded_df, expected_vars, lineage) -> Dict:
        """Map variables between uploaded and expected"""

        if expected_vars is None:
            expected_vars = []

        mappings = []
        found_vars = set(str(v).lower() for v in uploaded_df.columns) if uploaded_df is not None else set()
        unmatched_expected = set(v.lower() for v in expected_vars)

        # PASS 1: Exact matches
        for var in expected_vars:
            var_lower = var.lower()
            if var_lower in found_vars:
                mappings.append({
                    'expected': var,
                    'found': var_lower,
                    'confidence': 1.0,
                    'method': 'exact'
                })
                unmatched_expected.discard(var_lower)
                found_vars.discard(var_lower)

        # PASS 2: Fuzzy string matching
        for exp_var in list(unmatched_expected):
            best_match = None
            best_score = 0.75

            for found_var in found_vars:
                score = self._fuzzy_match(exp_var, found_var)
                if score > best_score:
                    best_score = score
                    best_match = found_var

            if best_match:
                mappings.append({
                    'expected': exp_var,
                    'found': best_match,
                    'confidence': best_score,
                    'method': 'fuzzy'
                })
                unmatched_expected.discard(exp_var)
                found_vars.discard(best_match)

        # PASS 3: Role-based matching
        for exp_var in list(unmatched_expected):
            exp_role = self._infer_variable_role(exp_var)

            for found_var in found_vars:
                found_role = self._infer_variable_role(found_var)

                if exp_role == found_role and found_role != 'unknown':
                    mappings.append({
                        'expected': exp_var,
                        'found': found_var,
                        'confidence': 0.75,
                        'method': 'semantic'
                    })
                    unmatched_expected.discard(exp_var)
                    found_vars.discard(found_var)
                    break

        return {
            'mappings': mappings,
            'unmatched': list(unmatched_expected),
            'extra_variables': list(found_vars)
        }

    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """Fuzzy match score 0-1"""
        str1, str2 = str1.lower(), str2.lower()

        if str1 == str2:
            return 1.0

        if str1 in str2 or str2 in str1:
            return 0.85

        # Simple Levenshtein distance approximation
        matching = sum(1 for c in str1 if c in str2)
        return matching / max(len(str1), len(str2))

    def _infer_variable_role(self, var_name: str) -> str:
        """Infer variable role from name"""
        var_lower = var_name.lower()

        for role, patterns in self.variable_role_patterns.items():
            for pattern in patterns:
                if pattern in var_lower:
                    return role

        return 'unknown'


# ============================================================================
# PHASE 2: MISSING DATA INTELLIGENCE
# ============================================================================

class MissingDataIntelligence:
    """Analyze missing data patterns and provide recommendations"""

    @staticmethod
    def analyze_missing_pattern(df, lineage, dataset_name) -> Dict:
        """Analyze missing data in a dataset"""

        if df is None or len(df) == 0:
            return {'missing_variables': [], 'alerts': []}

        dataset = lineage.datasets.get(dataset_name)
        if not dataset:
            return {'missing_variables': [], 'alerts': []}

        used_variables = dataset.required_variables or []
        df_columns = [str(c).lower() for c in df.columns]

        missing = [v for v in used_variables if v.lower() not in df_columns]

        alerts = []
        for var in missing:
            using_steps = [
                s.name for s in dataset.consumers
                if var in s.variables_used.get(dataset_name, [])
            ]

            # Assess severity
            if len(using_steps) > 2:
                severity = 'critical'
            elif any('REPORT' in s.upper() or 'MEANS' in s.upper() for s in using_steps):
                severity = 'high'
            else:
                severity = 'medium'

            alerts.append({
                'variable': var,
                'severity': severity,
                'used_by': using_steps,
                'recommendation': MissingDataIntelligence._recommend_handling(var, df)
            })

        return {
            'missing_variables': missing,
            'alerts': alerts,
            'completeness_score': ((len(used_variables) - len(missing)) / len(used_variables) * 100) if used_variables else 100
        }

    @staticmethod
    def _recommend_handling(var: str, df) -> Dict:
        """Recommend missing data strategy"""
        return {
            'action': 'contact_user',
            'message': f'Variable {var} is required but missing. Either provide the variable or adjust the SAS code.',
            'severity': 'BLOCKING'
        }


# ============================================================================
# PHASE 2: TRANSLATION READINESS SCORER
# ============================================================================

class TranslationReadinessScorer:
    """Score translation readiness across multiple dimensions"""

    @staticmethod
    def score(lineage: LineageGraph, uploaded_datasets: Dict, schema_validations: Dict) -> Dict:
        """Calculate multi-dimensional readiness score"""

        scores = {
            'data': TranslationReadinessScorer._score_data(lineage, uploaded_datasets),
            'intent': TranslationReadinessScorer._score_intent(lineage),
            'execution': TranslationReadinessScorer._score_execution(lineage, schema_validations),
        }

        weights = {'data': 0.5, 'intent': 0.3, 'execution': 0.2}
        overall = sum(scores[k] * weights[k] for k in scores)

        # If all required data is present, overall should be 100.0% (Translation Ready)
        if scores['data'] == 100.0:
            overall = 100.0

        return {
            'overall': round(overall, 1),
            'components': scores,
            'ready_for_translation': overall >= 80,
            'blockers': TranslationReadinessScorer._identify_blockers(lineage, uploaded_datasets)
        }

    @staticmethod
    def _score_data(lineage: LineageGraph, uploaded: Dict) -> float:
        """Data readiness: do we have required datasets?"""
        required = lineage.external_inputs
        if not required:
            return 100.0

        uploaded_names = set(uploaded.keys()) if uploaded else set()
        satisfied = len([d for d in required if d in uploaded_names])

        # 100% only if all required datasets are present
        if satisfied == len(required):
            return 100.0

        return (satisfied / len(required) * 100) if required else 100.0

    @staticmethod
    def _score_intent(lineage: LineageGraph) -> float:
        """Intent readiness: semantic clarity"""
        if not lineage.datasets:
            return 50.0

        semantic_clarity = len([
            d for d in lineage.datasets.values()
            if d.role != DatasetRole.UNKNOWN
        ]) / len(lineage.datasets)

        return semantic_clarity * 100

    @staticmethod
    def _score_execution(lineage: LineageGraph, schema_validations: Dict) -> float:
        """Execution readiness: variable mapping quality"""
        if not schema_validations:
            return 70.0

        total_mappings = 0
        high_confidence = 0

        for validations in schema_validations.values():
            if isinstance(validations, dict) and 'mappings' in validations:
                for m in validations['mappings']:
                    total_mappings += 1
                    if m.get('confidence', 0) > 0.85:
                        high_confidence += 1

        return (high_confidence / total_mappings * 100) if total_mappings else 70.0

    @staticmethod
    def _identify_blockers(lineage: LineageGraph, uploaded: Dict) -> List[str]:
        """Identify blockers to translation"""
        blockers = []

        required = lineage.external_inputs
        uploaded_names = set(uploaded.keys()) if uploaded else set()
        missing = [d for d in required if d not in uploaded_names]

        if missing:
            blockers.append(f"Missing datasets: {', '.join(missing)}")

        circular = TranslationReadinessScorer._detect_circular_deps(lineage)
        if circular:
            blockers.append(f"Circular dependencies detected: {', '.join(circular)}")

        return blockers

    @staticmethod
    def _detect_circular_deps(lineage: LineageGraph) -> List[str]:
        """Detect circular dependencies"""
        # Simplified: check for any dataset that is both input and output
        circular = []
        for ds_name, ds in lineage.datasets.items():
            if ds.producer and any(inp == ds_name for inp in ds.producer.inputs):
                circular.append(ds_name)
        return circular


# ============================================================================
# PHASE 3: AI MISSING DATA RECOMMENDER
# ============================================================================

class AIMissingDataRecommender:
    """Recommend missing data handling strategies"""

    MISSING_DATA_STRATEGIES = {
        'leave_missing': {
            'name': 'Leave Missing',
            'applicable_to': ['means', 'univariate', 'freq'],
            'description': 'SAS procedures handle missing values natively'
        },
        'mean': {
            'name': 'Mean Imputation',
            'applicable_to': ['continuous'],
            'description': 'Use variable mean for missing values'
        },
        'median': {
            'name': 'Median Imputation',
            'applicable_to': ['continuous'],
            'description': 'Use variable median for missing values'
        },
        'mode': {
            'name': 'Mode Imputation',
            'applicable_to': ['categorical'],
            'description': 'Use most frequent value for missing'
        },
        'locf': {
            'name': 'Last Observation Carried Forward',
            'applicable_to': ['time_series'],
            'description': 'Use previous non-missing value'
        },
        'nocb': {
            'name': 'Next Observation Carried Backward',
            'applicable_to': ['time_series'],
            'description': 'Use next non-missing value'
        },
        'interpolation': {
            'name': 'Linear Interpolation',
            'applicable_to': ['continuous', 'time_series'],
            'description': 'Interpolate between surrounding values'
        },
        'reject': {
            'name': 'Reject Dataset',
            'applicable_to': ['critical_variable'],
            'description': 'Cannot proceed without this variable'
        }
    }

    @staticmethod
    def recommend(var_name: str, missing_pct: float, datatype: str, usage_in_code: str, proc_types: List[str]) -> Dict:
        """Recommend missing data strategy"""

        # Determine variable importance
        if 'class' in usage_in_code.lower() or 'by' in usage_in_code.lower():
            criticality = 'critical'
        elif missing_pct > 50:
            criticality = 'high'
        elif missing_pct > 20:
            criticality = 'medium'
        else:
            criticality = 'low'

        # Detect variable type
        if datatype.lower() in ['char', 'text', 'varchar']:
            var_type = 'categorical'
        else:
            var_type = 'continuous'

        # Recommend strategy based on usage
        strategy = 'leave_missing'  # Default
        confidence = 0.5

        if criticality == 'critical':
            strategy = 'reject'
            confidence = 0.95
        elif 'PROC MEANS' in usage_in_code or 'PROC UNIVARIATE' in usage_in_code:
            strategy = 'leave_missing'
            confidence = 0.9
        elif 'PROC SQL' in usage_in_code and 'JOIN' in usage_in_code:
            strategy = 'reject'
            confidence = 0.95
        elif var_type == 'continuous' and missing_pct < 30:
            strategy = 'mean'
            confidence = 0.8
        elif var_type == 'categorical' and missing_pct < 30:
            strategy = 'mode'
            confidence = 0.8

        return {
            'variable': var_name,
            'missing_percent': missing_pct,
            'criticality': criticality,
            'recommended_strategy': strategy,
            'confidence': confidence,
            'reason': f"{AIMissingDataRecommender.MISSING_DATA_STRATEGIES[strategy]['description']}",
            'impact': f"{'Will block translation' if strategy == 'reject' else 'Low impact on execution'}"
        }


# ============================================================================
# PHASE 3: AI DEPENDENCY EXPLAINABILITY GENERATOR
# ============================================================================

class DependencyExplainabilityGenerator:
    """Generate explanations for dependencies"""

    @staticmethod
    def explain(ds_name: str, classification: Dict, lineage: LineageGraph, sas_code: str) -> Dict:
        """Generate comprehensive explanation"""

        dataset = lineage.datasets.get(ds_name)
        if not dataset:
            return {}

        # Find where it's used
        usage_locations = []
        for step in lineage.steps:
            if ds_name in step.inputs:
                usage_locations.append(step.name)

        # Find what it produces
        outputs = []
        for step in dataset.consumers if dataset else []:
            outputs.extend(step.outputs)

        # Business purpose
        business_purpose = DependencyExplainabilityGenerator._infer_business_purpose(ds_name, dataset.role)

        # Consequences
        if classification['upload_required'] is True:
            consequence = "Program will FAIL if this dataset is missing or incorrect"
            severity = 'CRITICAL'
        elif classification['upload_required'] == 'conditional':
            consequence = "Some analyses may be skipped or incomplete without this dataset"
            severity = 'WARNING'
        else:
            consequence = "Generated by the program; no upload needed"
            severity = 'INFO'

        return {
            'dataset': ds_name,
            'purpose': business_purpose,
            'used_by_steps': usage_locations,
            'produces_outputs': outputs,
            'business_meaning': f"This dataset provides {business_purpose}",
            'technical_role': f"Role: {dataset.role.value if dataset else 'unknown'}",
            'if_missing': consequence,
            'severity': severity,
            'upload_required': classification['upload_required'],
            'confidence': classification.get('confidence', 0.5)
        }

    @staticmethod
    def _infer_business_purpose(ds_name: str, role: 'DatasetRole') -> str:
        """Infer business purpose from name and role"""
        ds_lower = ds_name.lower()

        if 'dm' in ds_lower or role == DatasetRole.DEMOGRAPHICS:
            return "subject demographic attributes (age, sex, race, weight, etc.)"
        elif 'ae' in ds_lower or role == DatasetRole.ADVERSE_EVENTS:
            return "adverse event information (severity, onset date, causality, etc.)"
        elif 'sv' in ds_lower or 'visit' in ds_lower or role == DatasetRole.VISIT_DATA:
            return "visit and assessment timing information"
        elif 'adsl' in ds_lower or role == DatasetRole.ANALYSIS_DATASET:
            return "subject-level analysis dataset with baseline characteristics"
        else:
            return "clinical trial data"


# ============================================================================
# PHASE 3: SMART RECOMMENDATION ENGINE
# ============================================================================

class SmartRecommendationEngine:
    """Guide users through dependency resolution"""

    @staticmethod
    def recommend(lineage: LineageGraph, uploaded_datasets: Dict, classifications: Dict, sas_code: str) -> Dict:
        """Generate prioritized recommendations"""

        # Find missing datasets
        required = lineage.external_inputs
        uploaded_names = set(uploaded_datasets.keys()) if uploaded_datasets else set()
        missing = [d for d in required if d not in uploaded_names]

        # Prioritize by criticality
        priority_order = []
        for ds in missing:
            c = classifications.get(ds, {})
            if c.get('upload_required') is True:
                priority_order.append((ds, 'CRITICAL', 1))
            elif c.get('upload_required') == 'conditional':
                priority_order.append((ds, 'CONDITIONAL', 2))
            else:
                priority_order.append((ds, 'OPTIONAL', 3))

        priority_order.sort(key=lambda x: x[2])

        # Build recommendations
        recommendations = []
        for i, (ds_name, priority, _) in enumerate(priority_order, 1):
            recommendations.append({
                'step': i,
                'action': 'UPLOAD',
                'dataset': ds_name,
                'priority': priority,
                'guidance': f"Upload {ds_name} with correct schema and variable names"
            })

        # Add variable mapping suggestions
        var_suggestions = SmartRecommendationEngine._suggest_variable_mappings(lineage, uploaded_datasets)

        # Add next steps
        next_steps = []
        if missing:
            next_steps.append(f"Upload {len(missing)} missing dataset(s)")
        if var_suggestions:
            next_steps.append(f"Review {len(var_suggestions)} variable mappings")
        else:
            next_steps.append("Ready for translation")

        return {
            'upload_priority': recommendations,
            'variable_suggestions': var_suggestions,
            'next_steps': next_steps,
            'missing_count': len(missing),
            'satisfied_count': len(required) - len(missing),
            'readiness_estimate': max(0, min(100, (len(required) - len(missing)) / len(required) * 100)) if required else 100
        }

    @staticmethod
    def _suggest_variable_mappings(lineage: LineageGraph, uploaded_datasets: Dict) -> List[Dict]:
        """Suggest variable mappings"""
        suggestions = []
        for ds_name, df in uploaded_datasets.items():
            if ds_name in lineage.datasets:
                expected = lineage.datasets[ds_name].required_variables
                for var in expected or []:
                    if var.lower() not in [c.lower() for c in df.columns]:
                        # Find potential match
                        for col in df.columns:
                            if var.lower() in col.lower() or col.lower() in var.lower():
                                suggestions.append({
                                    'dataset': ds_name,
                                    'expected_variable': var,
                                    'suggested_match': col,
                                    'confidence': 0.75
                                })
                                break
        return suggestions


# ============================================================================
# PHASE 4: DATASET SEMANTIC COMPATIBILITY ENGINE
# ============================================================================

class SemanticCompatibilityEngine:
    """Match datasets by semantic meaning, not just filename"""

    @staticmethod
    def match(expected_name: str, uploaded_datasets: Dict, lineage: LineageGraph) -> List[Dict]:
        """Find semantic matches for expected dataset"""

        expected_ds = lineage.datasets.get(expected_name)
        if not expected_ds:
            return []

        matches = []
        for uploaded_name, df in uploaded_datasets.items():
            score = SemanticCompatibilityEngine._calculate_compatibility(
                expected_name, expected_ds, uploaded_name, df
            )
            if score > 0.6:
                matches.append({
                    'expected': expected_name,
                    'uploaded': uploaded_name,
                    'confidence': score,
                    'matching_variables': len([c for c in df.columns if c.lower() in [v.lower() for v in (expected_ds.required_variables or [])]])
                })

        return sorted(matches, key=lambda x: x['confidence'], reverse=True)

    @staticmethod
    def _calculate_compatibility(expected: str, expected_ds: 'Dataset', uploaded: str, df: pd.DataFrame) -> float:
        """Calculate semantic compatibility"""
        score = 0.0

        # Name similarity
        if expected.lower() in uploaded.lower() or uploaded.lower() in expected.lower():
            score += 0.3

        # Role matching
        expected_role = expected_ds.role.value if expected_ds else 'unknown'
        # Infer uploaded role from columns
        uploaded_cols = [c.lower() for c in df.columns]
        if any(x in uploaded_cols for x in ['usubjid', 'subjid']):
            score += 0.2
        if any(x in uploaded_cols for x in ['age', 'sex', 'race', 'weight']):
            score += 0.2 if expected_role == 'demographics' else 0.1

        # Schema similarity
        if len(df.columns) > 5:
            score += 0.2

        return min(score, 1.0)


# ============================================================================
# PHASE 4: TRANSLATION IMPACT ANALYZER (Detailed)
# ============================================================================

class DetailedTranslationImpactAnalyzer:
    """Analyze translation impact across multiple dimensions"""

    @staticmethod
    def analyze(lineage: LineageGraph, sas_code: str, uploaded_datasets: Dict) -> Dict:
        """Detailed per-dimension analysis"""

        return {
            'parser_readiness': DetailedTranslationImpactAnalyzer._score_parser(sas_code),
            'intent_clarity': DetailedTranslationImpactAnalyzer._score_intent(lineage),
            'execution_readiness': DetailedTranslationImpactAnalyzer._score_execution(lineage, uploaded_datasets),
            'package_intelligence': DetailedTranslationImpactAnalyzer._score_packages(sas_code),
            'validation_readiness': DetailedTranslationImpactAnalyzer._score_validation(lineage, uploaded_datasets),
            'overall_risk': DetailedTranslationImpactAnalyzer._calculate_overall_risk(lineage, uploaded_datasets)
        }

    @staticmethod
    def _score_parser(sas_code: str) -> Dict:
        """Score parser readiness"""
        score = 90  # Start high
        issues = []

        if '%MACRO' in sas_code.upper():
            score -= 10
            issues.append("Macros present - may affect parsing")
        if re.search(r'/\*.*?\*/', sas_code, re.DOTALL):
            issues.append("Block comments present")

        return {'score': score, 'status': 'Ready' if score > 80 else 'Review Needed', 'issues': issues}

    @staticmethod
    def _score_intent(lineage: LineageGraph) -> Dict:
        """Score intent clarity"""
        score = 75
        for ds in lineage.datasets.values():
            if ds.role != DatasetRole.UNKNOWN:
                score += 5

        return {'score': min(score, 100), 'status': 'Clear' if score > 80 else 'Unclear'}

    @staticmethod
    def _score_execution(lineage: LineageGraph, uploaded_datasets: Dict) -> Dict:
        """Score execution readiness"""
        required = lineage.external_inputs
        uploaded = set(uploaded_datasets.keys()) if uploaded_datasets else set()
        missing = len([d for d in required if d not in uploaded])

        score = max(0, (len(required) - missing) / len(required) * 100) if required else 100
        return {'score': score, 'status': 'Ready' if missing == 0 else f'{missing} datasets missing'}

    @staticmethod
    def _score_packages(sas_code: str) -> Dict:
        """Score package intelligence"""
        procs = re.findall(r'PROC\s+(\w+)', sas_code, re.IGNORECASE)
        score = 80

        unsupported = ['LOGISTIC', 'GENMOD', 'MIXED', 'GLIMMIX']
        for proc in procs:
            if proc.upper() in unsupported:
                score -= 10

        return {'score': max(0, score), 'procs_found': procs}

    @staticmethod
    def _score_validation(lineage: LineageGraph, uploaded_datasets: Dict) -> Dict:
        """Score validation readiness"""
        score = 75
        if len(uploaded_datasets) > 0:
            score += 10
        if lineage.qc_datasets:
            score += 10

        return {'score': min(score, 100), 'status': 'Ready' if score > 75 else 'Needs Review'}

    @staticmethod
    def _calculate_overall_risk(lineage: LineageGraph, uploaded_datasets: Dict) -> str:
        """Calculate overall risk level"""
        required = lineage.external_inputs
        uploaded = set(uploaded_datasets.keys()) if uploaded_datasets else set()
        missing_count = len([d for d in required if d not in uploaded])

        if missing_count > len(required) * 0.3:
            return 'HIGH'
        elif missing_count > 0:
            return 'MEDIUM'
        else:
            return 'LOW'


# ============================================================================
# PHASE 4: CRITICAL VARIABLE DETECTOR
# ============================================================================

class CriticalVariableDetector:
    """Detect variables that are critical for translation"""

    @staticmethod
    def detect(lineage: LineageGraph, sas_code: str, uploaded_datasets: Dict) -> Dict:
        """Detect critical variables"""

        critical = []
        important = []
        optional = []

        for ds_name, dataset in lineage.datasets.items():
            if ds_name not in uploaded_datasets:
                continue

            df = uploaded_datasets[ds_name]
            for col in df.columns:
                col_lower = col.lower()

                # Critical: Join keys, IDs, treatment
                if any(x in col_lower for x in ['usubjid', 'subjid', 'id', 'trt', 'treatment']):
                    critical.append({'variable': col, 'dataset': ds_name, 'reason': 'Join key or treatment variable'})
                # Important: Statistical variables
                elif any(x in col_lower for x in ['age', 'baseline', 'visit', 'day']):
                    important.append({'variable': col, 'dataset': ds_name, 'reason': 'Statistical or grouping variable'})
                else:
                    optional.append({'variable': col, 'dataset': ds_name, 'reason': 'Reporting or derived variable'})

        return {
            'critical_variables': critical,
            'important_variables': important,
            'optional_variables': optional,
            'total_critical': len(critical),
            'will_block_if_missing': len(critical) > 0
        }


# ============================================================================
# PHASE 4+: DATASET ROLE DETECTOR & VARIABLE USAGE CLASSIFIER
# ============================================================================

class DatasetRoleDetector:
    """Detect dataset role more accurately"""

    @staticmethod
    def detect_role(dataset_name: str, df: pd.DataFrame) -> str:
        """Detect dataset role from name and schema"""
        ds_lower = dataset_name.lower()
        cols_lower = [c.lower() for c in df.columns]

        if any(x in ds_lower for x in ['dm', 'demographic']):
            return 'SDTM Demographics'
        elif any(x in ds_lower for x in ['ae', 'adverse']):
            return 'SDTM Adverse Events'
        elif any(x in ds_lower for x in ['adsl', 'adsl']):
            return 'ADaM Subject Level'
        elif any(x in ds_lower for x in ['qc', 'compare']):
            return 'QC Reference'
        elif 'lookup' in ds_lower or 'code' in ds_lower:
            return 'Lookup/Reference'
        elif 'raw' in ds_lower or 'source' in ds_lower:
            return 'Raw Input'
        elif 'adam' in ds_lower:
            return 'ADaM Analysis'
        else:
            return 'Unknown'


class VariableUsageClassifier:
    """Classify variable usage patterns"""

    @staticmethod
    def classify(var_name: str, sas_code: str) -> Dict:
        """Classify how variable is used"""
        var_lower = var_name.lower()

        usage = {
            'join_key': False,
            'statistical': False,
            'grouping': False,
            'reporting': False,
            'classification': False
        }

        # Look for usage patterns
        if any(x in sas_code.upper() for x in [f'BY {var_name}', f'BY {var_lower}', 'MERGE ON']):
            usage['join_key'] = True
        if any(x in sas_code.upper() for x in [f'CLASS {var_name}', f'VAR {var_name}', f'PROC MEANS']):
            usage['statistical'] = True
        if 'CLASS' in sas_code.upper():
            usage['grouping'] = True
        if 'PROC REPORT' in sas_code.upper():
            usage['reporting'] = True

        return usage


# ============================================================================
# DEPENDENCY HEALTH SCORE
# ============================================================================

class DependencyHealthScorer:
    """Score overall dependency health"""

    @staticmethod
    def score(lineage: LineageGraph, uploaded_datasets: Dict, classifications: Dict) -> Dict:
        """Calculate comprehensive health score"""

        required = lineage.external_inputs
        uploaded = set(uploaded_datasets.keys()) if uploaded_datasets else set()
        satisfied = len([d for d in required if d in uploaded])
        missing_datasets = [d for d in required if d not in uploaded]
        missing_count = len(missing_datasets)
        critical_missing = len([d for d in missing_datasets if classifications.get(d, {}).get('upload_required') is True])

        health_score = max(0, (satisfied / len(required) * 100)) if required else 100

        return {
            'health_score': round(health_score, 1),
            'satisfied_count': satisfied,
            'missing_count': missing_count,
            'critical_missing_count': critical_missing,
            'health_status': 'Excellent' if health_score > 90 else 'Good' if health_score > 75 else 'Fair' if health_score > 50 else 'Poor'
        }


# ============================================================================
# MAIN DEPENDENCY INTELLIGENCE ENGINE
# ============================================================================

class DependencyIntelligenceEnginev2:
    """Complete semantic dependency analysis system (Phase 1-4 + Enterprise)"""

    def __init__(self):
        self.lineage_builder = LineageBuilder()
        self.classifier = DependencyClassifier()
        self.variable_mapper = SemanticVariableMapper()
        self.missing_data = MissingDataIntelligence()
        self.readiness_scorer = TranslationReadinessScorer()

        # Phase 3: AI Intelligence
        self.missing_data_recommender = AIMissingDataRecommender()
        self.explainability_generator = DependencyExplainabilityGenerator()
        self.recommendation_engine = SmartRecommendationEngine()

        # Phase 4: Advanced
        self.semantic_compatibility = SemanticCompatibilityEngine()
        self.translation_impact_analyzer = DetailedTranslationImpactAnalyzer()
        self.critical_detector = CriticalVariableDetector()

        # Enterprise
        self.health_scorer = DependencyHealthScorer()
        self.role_detector = DatasetRoleDetector()
        self.usage_classifier = VariableUsageClassifier()

    def analyze(self, sas_code: str, uploaded_datasets: Dict[str, pd.DataFrame]) -> Dict:
        """Complete analysis pipeline (Phase 1-4 + Enterprise)"""

        # ── PHASE 1: Build lineage ──
        lineage = self.lineage_builder.build(sas_code)

        # ── PHASE 1: Classify dependencies ──
        classifications = self.classifier.classify(lineage)

        # ── PHASE 2: Map variables ──
        schema_validations = {}
        for ds_name, ds in lineage.datasets.items():
            if ds_name in uploaded_datasets:
                schema_validations[ds_name] = self.variable_mapper.map_dataset_variables(
                    uploaded_datasets[ds_name],
                    ds.required_variables,
                    lineage
                )

        # ── PHASE 2: Missing data intelligence ──
        missing_data = {}
        for ds_name, ds in lineage.datasets.items():
            if ds_name in uploaded_datasets:
                missing_data[ds_name] = self.missing_data.analyze_missing_pattern(
                    uploaded_datasets[ds_name],
                    lineage,
                    ds_name
                )

        # ── PHASE 2: Translation readiness ──
        readiness = self.readiness_scorer.score(lineage, uploaded_datasets, schema_validations)

        # ── PHASE 3: AI Missing Data Recommendations ──
        missing_data_recommendations = {}
        for ds_name, df in uploaded_datasets.items():
            if ds_name in missing_data:
                md = missing_data[ds_name]
                if md.get('missing_variables'):
                    recommendations = {}
                    for var in md['missing_variables']:
                        rec = self.missing_data_recommender.recommend(
                            var_name=var,
                            missing_pct=0,
                            datatype='numeric',
                            usage_in_code=sas_code,
                            proc_types=[s.step_type.value for s in lineage.steps]
                        )
                        recommendations[var] = rec
                    missing_data_recommendations[ds_name] = recommendations

        # ── PHASE 3: AI Dependency Explainability ──
        explainability = {}
        for ds_name, classification in classifications.items():
            explainability[ds_name] = self.explainability_generator.explain(
                ds_name, classification, lineage, sas_code
            )

        # ── PHASE 3: Smart Recommendations ──
        recommendations = self.recommendation_engine.recommend(
            lineage, uploaded_datasets, classifications, sas_code
        )

        # ── PHASE 4: Semantic Compatibility Matching ──
        required_datasets = lineage.external_inputs
        compatibility_matches = {}
        for req_ds in required_datasets:
            matches = self.semantic_compatibility.match(req_ds, uploaded_datasets, lineage)
            if matches:
                compatibility_matches[req_ds] = matches

        # ── PHASE 4: Detailed Translation Impact ──
        translation_impact = self.translation_impact_analyzer.analyze(lineage, sas_code, uploaded_datasets)

        # ── PHASE 4: Critical Variables ──
        critical_variables = self.critical_detector.detect(lineage, sas_code, uploaded_datasets)

        # ── ENTERPRISE: Dataset Roles ──
        dataset_roles = {}
        for ds_name, df in uploaded_datasets.items():
            dataset_roles[ds_name] = self.role_detector.detect_role(ds_name, df)

        # ── ENTERPRISE: Variable Classification ──
        variable_classification = {}
        for ds_name, df in uploaded_datasets.items():
            for col in df.columns:
                if ds_name not in variable_classification:
                    variable_classification[ds_name] = {}
                variable_classification[ds_name][col] = self.usage_classifier.classify(col, sas_code)

        # ── ENTERPRISE: Dependency Health Score ──
        health_score = self.health_scorer.score(lineage, uploaded_datasets, classifications)

        return {
            # Phase 1-2 (Core)
            'lineage_graph': lineage.to_dict(),
            'classifications': classifications,
            'schema_validations': schema_validations,
            'missing_data_intelligence': missing_data,
            'readiness': readiness,
            'upload_required': [
                d for d, c in classifications.items()
                if c['upload_required'] is True
            ],
            'all_datasets': list(lineage.datasets.keys()),

            # Phase 3 (AI Intelligence)
            'missing_data_recommendations': missing_data_recommendations,
            'dependency_explainability': explainability,
            'smart_recommendations': recommendations,

            # Phase 4 (Advanced)
            'semantic_compatibility_matches': compatibility_matches,
            'translation_impact': translation_impact,
            'critical_variables': critical_variables,

            # Enterprise
            'dataset_roles': dataset_roles,
            'variable_classification': variable_classification,
            'dependency_health': health_score
        }
