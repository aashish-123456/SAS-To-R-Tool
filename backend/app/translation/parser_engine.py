"""
Engine 1 — Parser Engine
Answers: WHAT is written in the SAS code?
Detects every construct, function, keyword, variable, and data element.
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParseResult:
    raw_code: str
    cleaned_code: str
    ast: List[Dict]
    inline_data: List[Any]

    # Structural elements
    data_steps: List[Dict]
    proc_steps: List[Dict]
    macros: List[Dict]

    # Language tokens
    functions: Set[str]
    keywords: Set[str]
    operators: Set[str]

    # Variables and datasets
    variables: Dict[str, str]          # name → type (numeric / character / unknown)
    datasets: Dict[str, str]           # name → role (input / output / both)

    # Control-flow
    if_else_chains: List[Dict]
    do_loops: List[Dict]

    # Statistics
    statistics_requested: Set[str]

    # Summary counters
    total_statements: int
    proc_types: List[str]

    # Feature flags
    has_macros: bool
    has_sql: bool
    has_merge: bool
    has_array: bool
    has_retain: bool
    has_output: bool
    has_format: bool
    has_proc_reg: bool
    has_proc_glm: bool
    has_proc_mixed: bool
    has_clinical_procs: bool

    # Hash objects (optional, defaults to empty dict)
    hash_objects: Dict[str, Dict] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class ParserEngine:
    """
    First sub-layer of the Translation Module.
    Reads every SAS construct, function, and keyword so subsequent engines
    have a complete structural picture of the code.
    """

    # ── knowledge bases ────────────────────────────────────────────────────────

    SAS_FUNCTIONS: Set[str] = {
        "abs", "ceil", "floor", "round", "int", "mod",
        "sum", "mean", "min", "max", "std", "var", "median",
        "n", "nmiss", "range",
        "upcase", "lowcase", "substr", "index", "length", "trim", "strip",
        "compress", "cats", "catt", "catx",
        "input", "put",
        "today", "date", "year", "month", "day", "datepart",
        "log", "log2", "log10", "exp", "sqrt",
        "ifn", "ifc", "coalesce",
        "lag", "dif",
        "first", "last",
        "scan", "tranwrd", "anydigit", "anyalpha",
        "intck", "intnx", "datdif",
        "prxmatch", "prxchange",
    }

    SAS_KEYWORDS: Set[str] = {
        "data", "set", "merge", "by", "if", "then", "else", "end", "do",
        "run", "quit", "input", "output", "keep", "drop", "rename", "retain",
        "array", "where", "format", "informat", "label", "attrib",
        "length", "infile", "filename", "libname",
        "proc", "var", "class", "tables", "model", "means", "freq", "sort",
        "print", "sql", "transpose", "export", "import",
        "select", "from", "group", "order", "having",
        "create", "insert", "update", "delete",
        "cards", "datalines",
    }

    PROC_PURPOSE_MAP: Dict[str, str] = {
        "means":     "descriptive_statistics",
        "freq":      "frequency_analysis",
        "sort":      "data_sorting",
        "print":     "data_display",
        "sql":       "database_operations",
        "transpose": "data_reshaping",
        "export":    "data_export",
        "import":    "data_import",
        "reg":       "linear_regression",
        "glm":       "analysis_of_variance",
        "mixed":     "mixed_models",
        "logistic":  "logistic_regression",
        "phreg":     "cox_regression",
        "lifetest":  "survival_analysis",
        "univariate":"univariate_analysis",
        "corr":      "correlation_analysis",
        "factor":    "factor_analysis",
        "cluster":   "cluster_analysis",
        "report":    "reporting",
        "tabulate":  "tabulation",
        "format":    "format_definition",
        "contents":  "dataset_metadata",
        "datasets":  "dataset_management",
        "fcmp":      "custom_functions",
    }

    # ── public API ─────────────────────────────────────────────────────────────

    def parse(self, sas_code: str) -> ParseResult:
        """Return a fully-populated ParseResult for the given SAS source."""
        cleaned = self._clean_code(sas_code)

        # Delegate AST construction to the existing SAS parser
        from app.services.sas_parser import SASParser
        existing_parser = SASParser()
        try:
            ast, inline_data = existing_parser.parse(cleaned)
        except Exception:
            ast, inline_data = [], []

        data_steps      = self._extract_data_steps(cleaned, ast)
        proc_steps      = self._extract_proc_steps(cleaned, ast)
        macros          = self._extract_macros(sas_code)
        # Extract hash objects from macros
        hash_objects    = {m['name']: {k: m.get(k) for k in ['dataset', 'key', 'data']}
                          for m in macros if m.get('type') == 'hash_object'}
        functions       = self._detect_functions(cleaned)
        keywords        = self._detect_keywords(cleaned)
        operators       = self._detect_operators(cleaned)
        variables       = self._extract_variables(cleaned, ast)
        datasets        = self._extract_datasets(cleaned, ast)
        if_else_chains  = self._extract_if_else(cleaned, ast)
        do_loops        = self._extract_do_loops(cleaned)
        statistics      = self._extract_statistics(cleaned, ast)
        proc_types      = list(dict.fromkeys(
            p.get("proc_type", "unknown") for p in proc_steps
        ))

        code_lc = sas_code.lower()
        return ParseResult(
            raw_code        = sas_code,
            cleaned_code    = cleaned,
            ast             = ast,
            inline_data     = inline_data,
            data_steps      = data_steps,
            proc_steps      = proc_steps,
            macros          = macros,
            hash_objects    = hash_objects,
            functions       = functions,
            keywords        = keywords,
            operators       = operators,
            variables       = variables,
            datasets        = datasets,
            if_else_chains  = if_else_chains,
            do_loops        = do_loops,
            statistics_requested = statistics,
            total_statements= len(ast),
            proc_types      = proc_types,
            has_macros      = bool(macros) or "%" in sas_code,
            has_sql         = any(n.get("type") == "proc_sql" for n in ast)
                              or bool(re.search(r"\bproc\s+sql\b", code_lc)),
            has_merge       = any("merge" in n.get("type", "") for n in ast)
                              or bool(re.search(r"\bmerge\b", code_lc)),
            has_array       = bool(re.search(r"\barray\b", code_lc)),
            has_retain      = bool(re.search(r"\bretain\b", code_lc)),
            has_output      = bool(re.search(r"\boutput\s*;", code_lc)),
            has_format      = bool(re.search(r"\bformat\b", code_lc)),
            has_proc_reg    = any(n.get("type") == "proc_reg"  for n in ast)
                              or bool(re.search(r"\bproc\s+reg\b",  code_lc)),
            has_proc_glm    = any(n.get("type") == "proc_glm"  for n in ast)
                              or bool(re.search(r"\bproc\s+glm\b",  code_lc)),
            has_proc_mixed  = bool(re.search(r"\bproc\s+mixed\b",   code_lc)),
            has_clinical_procs = bool(
                re.search(r"\bproc\s+(phreg|lifetest|logistic|mixed)\b", code_lc)
            ),
        )

    # ── private helpers ────────────────────────────────────────────────────────

    def _clean_code(self, code: str) -> str:
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"^\s*\*[^;]*;", "", code, flags=re.MULTILINE)
        return code.strip()

    def _extract_data_steps(self, code: str, ast: List[Dict]) -> List[Dict]:
        steps: List[Dict] = []
        seen: Set[str] = set()

        for n in ast:
            if n.get("type") == "data_step":
                ds = n.get("dataset", "work")
                seen.add(ds)
                step = {
                    "dataset":           ds,
                    "sources":           [],
                    "operations":        [],
                    "variables_defined": [],
                    "variables_kept":    n.get("keep", []),
                    "variables_dropped": n.get("drop", []),
                }
                # Find SET/MERGE nodes that feed this step
                for m in ast:
                    if m.get("type") in ("set", "merge") and m.get("dataset"):
                        step["sources"].append(m["dataset"])
                steps.append(step)

        for m in re.finditer(r"\bdata\s+(\w+)\s*;", code, re.IGNORECASE):
            ds = m.group(1)
            if ds not in seen:
                seen.add(ds)
                steps.append({
                    "dataset":           ds,
                    "sources":           [],
                    "operations":        [],
                    "variables_defined": [],
                    "variables_kept":    [],
                    "variables_dropped": [],
                })
        return steps

    def _extract_proc_steps(self, code: str, ast: List[Dict]) -> List[Dict]:
        steps: List[Dict] = []
        seen: Set[str] = set()

        for n in ast:
            node_type = n.get("type", "")
            if node_type.startswith("proc_"):
                proc_name = node_type[5:]
                seen.add(proc_name)
                steps.append({
                    "proc_type":      proc_name,
                    "purpose":        self.PROC_PURPOSE_MAP.get(proc_name, "data_analysis"),
                    "input_dataset":  n.get("dataset", n.get("data", "")),
                    "output_dataset": n.get("out", ""),
                    "variables":      n.get("variables", []),
                    "by_vars":        n.get("by", []),
                    "class_vars":     n.get("class", []),
                    "options":        n.get("options", {}),
                    "statistics":     n.get("statistics", []),
                })

        for m in re.finditer(r"\bproc\s+(\w+)\b", code, re.IGNORECASE):
            proc_name = m.group(1).lower()
            # For PROC IMPORT, allow multiple instances; for others, check seen
            if proc_name == "import" or (proc_name not in seen and proc_name not in ("run", "quit")):
                if proc_name != "import":
                    seen.add(proc_name)

                # Special handling for PROC IMPORT
                if proc_name == "import":
                    # Extract OUT= dataset name (search up to run/quit)
                    code_section = code[m.start():m.start()+500]
                    out_match = re.search(
                        r"out\s*=\s*(\w+)", code_section, re.IGNORECASE
                    )
                    out_ds = out_match.group(1) if out_match else "imported_data"

                    # Extract DATAFILE= path
                    datafile_match = re.search(
                        r'datafile\s*=\s*["\']?([^"\';\s]+)["\']?',
                        code_section, re.IGNORECASE
                    )
                    datafile = datafile_match.group(1) if datafile_match else ""

                    steps.append({
                        "proc_type":      "import",
                        "purpose":        "data_import",
                        "input_dataset":  "",
                        "output_dataset": out_ds,
                        "variables":      [],
                        "by_vars":        [],
                        "class_vars":     [],
                        "options":        {"datafile": datafile},
                        "statistics":     [],
                    })
                else:
                    steps.append({
                        "proc_type":      proc_name,
                        "purpose":        self.PROC_PURPOSE_MAP.get(proc_name, "data_analysis"),
                        "input_dataset":  "",
                        "output_dataset": "",
                        "variables":      [],
                        "by_vars":        [],
                        "class_vars":     [],
                        "options":        {},
                        "statistics":     [],
                    })
        return steps

    def _extract_macros(self, code: str) -> List[Dict]:
        macros: List[Dict] = []
        macro_re = re.compile(r"%macro\s+(\w+)\s*(?:\((.*?)\))?\s*;", re.IGNORECASE)
        for m in macro_re.finditer(code):
            macros.append({
                "name":       m.group(1),
                "parameters": [p.strip() for p in (m.group(2) or "").split(",") if p.strip()],
            })
        macro_vars = list(set(re.findall(r"&(\w+)", code)))
        if macro_vars:
            macros.append({"macro_variables": macro_vars})

        # Extract hash objects
        hash_re = re.compile(
            r"declare\s+hash\s+(\w+)\s*\(\s*(?:dataset\s*:\s*['\"]?(\w+)['\"]?)?\s*\);",
            re.IGNORECASE | re.DOTALL
        )
        for m in hash_re.finditer(code):
            hash_name = m.group(1)
            dataset = m.group(2)

            # Find defineKey and defineData calls for this hash
            hash_section = code[m.start():m.start()+1000]
            key_match = re.search(
                rf"{re.escape(hash_name)}\.defineKey\s*\(\s*['\"]?(\w+)['\"]?\s*\)",
                hash_section, re.IGNORECASE
            )
            data_match = re.search(
                rf"{re.escape(hash_name)}\.defineData\s*\(\s*([^)]+)\s*\)",
                hash_section, re.IGNORECASE
            )

            key_var = key_match.group(1) if key_match else ""
            data_vars = [v.strip().strip("'\"") for v in (data_match.group(1).split(",") if data_match else [])]

            macros.append({
                "type": "hash_object",
                "name": hash_name,
                "dataset": dataset,
                "key": key_var,
                "data": data_vars,
            })

        return macros

    def _detect_functions(self, code: str) -> Set[str]:
        found: Set[str] = set()
        for fn in self.SAS_FUNCTIONS:
            if re.search(rf"\b{re.escape(fn)}\s*\(", code, re.IGNORECASE):
                found.add(fn)
        for m in re.finditer(r"\b([a-z_]\w*)\s*\(", code, re.IGNORECASE):
            fname = m.group(1).lower()
            if fname not in {"data", "proc", "if", "do", "while", "until", "then", "else"}:
                found.add(fname)
        return found

    def _detect_keywords(self, code: str) -> Set[str]:
        found: Set[str] = set()
        for kw in self.SAS_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", code, re.IGNORECASE):
                found.add(kw.lower())
        return found

    def _detect_operators(self, code: str) -> Set[str]:
        ops: Set[str] = set()
        checks = [
            (r"\b(AND|&)\b",     "AND"),
            (r"\b(OR|\|)\b",     "OR"),
            (r"\bNOT\b|!",       "NOT"),
            (r"\bIN\b",          "IN"),
            (r"\bBETWEEN\b",     "BETWEEN"),
            (r"\bLIKE\b",        "LIKE"),
            (r"=",               "="),
            (r">",               ">"),
            (r"<",               "<"),
            (r"\*\*",            "**"),
        ]
        for pattern, label in checks:
            if re.search(pattern, code, re.IGNORECASE):
                ops.add(label)
        return ops

    def _extract_variables(self, code: str, ast: List[Dict]) -> Dict[str, str]:
        variables: Dict[str, str] = {}
        upper_keywords = {kw.upper() for kw in self.SAS_KEYWORDS}

        for n in ast:
            if n.get("type") == "input":
                for var in n.get("variables", []):
                    if isinstance(var, dict):
                        vname = var.get("name", "")
                        vtype = "character" if var.get("is_char") else "numeric"
                    else:
                        vname = str(var)
                        vtype = "unknown"
                    if vname:
                        variables[vname] = vtype

        for m in re.finditer(r"\b([A-Za-z_]\w*)\s*=\s*", code):
            vname = m.group(1)
            if vname.upper() not in upper_keywords and vname not in variables:
                variables[vname] = "numeric"

        for m in re.finditer(r"\blength\s+(.*?);", code, re.IGNORECASE | re.DOTALL):
            parts = m.group(1).split()
            for i, p in enumerate(parts):
                if p.startswith("$") and i > 0:
                    variables[parts[i - 1]] = "character"
                elif i + 1 < len(parts) and parts[i + 1].startswith("$"):
                    variables[p] = "character"
        return variables

    def _extract_datasets(self, code: str, ast: List[Dict]) -> Dict[str, str]:
        datasets: Dict[str, str] = {}

        for n in ast:
            if n.get("type") == "data_step":
                ds = n.get("dataset", "")
                if ds:
                    datasets[ds] = "output"

        for n in ast:
            if n.get("type") in ("set", "merge"):
                ds = n.get("dataset", "")
                if ds:
                    datasets[ds] = "both" if ds in datasets else "input"

        for n in ast:
            if n.get("type", "").startswith("proc_"):
                for key in ("dataset", "data"):
                    ds = n.get(key, "")
                    if ds:
                        if ds in datasets and datasets[ds] == "output":
                            datasets[ds] = "both"
                        elif ds not in datasets:
                            datasets[ds] = "input"
                out = n.get("out", "")
                if out:
                    datasets[out] = "output"
        return datasets

    def _extract_if_else(self, code: str, ast: List[Dict]) -> List[Dict]:
        chains: List[Dict] = []
        for n in ast:
            if n.get("type") in ("if_then_else", "if"):
                chains.append({
                    "condition":     n.get("condition", ""),
                    "then_action":   n.get("then", ""),
                    "else_action":   n.get("else", ""),
                    "is_classification": self._is_classification(n),
                })
        # Also catch raw IF-THEN in code not captured by AST
        pattern = re.compile(
            r"\bif\b\s*(.+?)\s*\bthen\b\s*(.+?)(?:;\s*(?:else\b\s*(.+?))?)?;",
            re.IGNORECASE | re.DOTALL,
        )
        for m in pattern.finditer(code):
            chains.append({
                "condition":     m.group(1).strip()[:200],
                "then_action":   m.group(2).strip()[:200],
                "else_action":   (m.group(3) or "").strip()[:200],
                "is_classification": bool(
                    re.search(r'=\s*["\']', m.group(2) or "") or
                    re.search(r'=\s*["\']', m.group(3) or "")
                ),
            })
        # Deduplicate by condition text
        seen: Set[str] = set()
        unique: List[Dict] = []
        for c in chains:
            key = c["condition"][:80]
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def _is_classification(self, node: Dict) -> bool:
        then_str = str(node.get("then", ""))
        else_str = str(node.get("else", ""))
        return bool(
            re.search(r'=\s*["\']', then_str) or
            re.search(r'=\s*["\']', else_str)
        )

    def _extract_do_loops(self, code: str) -> List[Dict]:
        loops: List[Dict] = []
        for m in re.finditer(
            r"\bdo\s+(\w+)\s*=\s*(\S+)\s*to\s*(\S+)", code, re.IGNORECASE
        ):
            loops.append({
                "variable": m.group(1),
                "from":     m.group(2),
                "to":       m.group(3),
                "type":     "for_loop",
            })
        if re.search(r"\bdo\s+while\b", code, re.IGNORECASE):
            loops.append({"type": "while_loop"})
        if re.search(r"\bdo\s+until\b", code, re.IGNORECASE):
            loops.append({"type": "until_loop"})
        return loops

    def _extract_statistics(self, code: str, ast: List[Dict]) -> Set[str]:
        stats: Set[str] = set()
        for n in ast:
            if n.get("type") == "proc_means":
                for stat in n.get("statistics", []):
                    stats.add(stat.lower())
        keywords = {
            "n", "mean", "std", "min", "max", "median",
            "sum", "range", "skewness", "kurtosis", "var",
            "cv", "stderr", "nmiss", "q1", "q3",
        }
        for kw in keywords:
            if re.search(rf"\b{kw}\b", code, re.IGNORECASE):
                stats.add(kw)
        return stats
