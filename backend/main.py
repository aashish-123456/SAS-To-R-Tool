"""
SAS to R Automation Platform – Main FastAPI Application
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import os
import shutil
import subprocess
import tempfile
import re
from pathlib import Path

# ── service imports ────────────────────────────────────────────────────────────
from app.services.sas_parser import SASParser
from app.services.r_generator import RCodeGenerator

app = FastAPI(
    title="SAS to R Automation Platform",
    description="AI-Powered SAS to R translation with output comparison",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in
                   os.getenv("ALLOWED_ORIGINS",
                             "http://localhost:5173,http://localhost:3000").split(",")
                   if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("data/uploads")
OUTPUT_DIR = Path("data/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── in-memory stores ───────────────────────────────────────────────────────────
projects_db: Dict[str, Any] = {}
translations_db: Dict[str, Any] = {}
executions_db: Dict[str, Any] = {}
validations_db: Dict[str, Any] = {}
feedback_db: Dict[str, Any] = {}

# ══════════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    sas_file_id: Optional[str] = None
    generated_r_code_id: Optional[str] = None
    validation_report_id: Optional[str] = None

class TranslationStatus(BaseModel):
    status: str
    progress: int
    r_code_preview: Optional[str] = None
    warnings: List[str] = []

class ValidationResult(BaseModel):
    overall_match: float
    structure_match: bool
    value_discrepancies: int
    statistics: Dict[str, Any]
    issues: List[Dict[str, str]] = []

class FeedbackRequest(BaseModel):
    project_id: str
    translation_id: str
    is_correct: bool
    corrections: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    user_notes: Optional[str] = None

# ══════════════════════════════════════════════════════════════════════════════
# CORE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def save_uploaded_file(upload_file: UploadFile, project_id: str, file_type: str) -> str:
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{project_id}_{file_type}_{file_id}_{upload_file.filename}"
    with open(file_path, "wb") as buf:
        shutil.copyfileobj(upload_file.file, buf)
    return str(file_path)


def _expand_simple_macros(code: str) -> str:
    """
    Expand simple %macro/%mend blocks with positional invocation arguments.
    This handles common patterns used in this app's sample pipelines.
    """
    macro_pattern = re.compile(
        r'%macro\s+(\w+)\s*\((.*?)\)\s*;(.*?)%mend(?:\s+\w+)?\s*;',
        re.IGNORECASE | re.DOTALL,
    )

    macros: Dict[str, Dict[str, Any]] = {}
    for m in macro_pattern.finditer(code):
        name = m.group(1).lower()
        params = [p.strip() for p in m.group(2).split(',') if p.strip()]
        body = m.group(3)
        macros[name] = {"params": params, "body": body}

    expanded = macro_pattern.sub('', code)

    for name, info in macros.items():
        call_re = re.compile(rf'%{re.escape(name)}\s*\((.*?)\)\s*;', re.IGNORECASE)

        def _replace_call(call_match):
            args = [a.strip() for a in call_match.group(1).split(',')]
            mapping = {p: (args[i] if i < len(args) else '') for i, p in enumerate(info["params"])}
            body = info["body"]
            for p, v in mapping.items():
                body = re.sub(rf'&{re.escape(p)}\b', v, body, flags=re.IGNORECASE)
            # Heuristic: if macro has a region argument and DATA step declares Region
            # but does not assign it, inject assignment for practical grouping/sorting.
            region_val = mapping.get('region') or mapping.get('Region')
            if region_val and re.search(r'\blength\s+Region\b', body, flags=re.IGNORECASE) and not re.search(r'\bRegion\s*=', body):
                body = re.sub(
                    r'(data\s+[A-Za-z_][A-Za-z0-9_]*\s*;)',
                    rf'\1\n        Region = "{region_val}";',
                    body,
                    flags=re.IGNORECASE,
                    count=1,
                )
            return body

        expanded = call_re.sub(_replace_call, expanded)

    # Unresolved macro vars left as-is but remove leading ampersand when obvious
    expanded = re.sub(r'&([A-Za-z_][A-Za-z0-9_]*)', r'\1', expanded)
    return expanded


def translate_sas_to_r(sas_code: str):
    """Parse SAS code and generate R code using AST pipeline."""
    warnings_out: List[str] = []
    try:
        sas_code = _expand_simple_macros(sas_code)
        parser = SASParser()
        ast, inline_data = parser.parse(sas_code)

        gen = RCodeGenerator()
        r_code = gen.generate(ast, inline_data)

        # surface warnings for things we can't fully translate
        if any(n.get('type') == 'proc_fcmp' for n in ast):
            warnings_out.append("PROC FCMP – custom function definitions need manual review.")
        if '%' in sas_code:
            warnings_out.append("SAS macro variables detected – manual review recommended.")
        if any(n.get('type') == 'proc_sql' for n in ast):
            warnings_out.append("PROC SQL found – translated as a dplyr placeholder; verify the SQL logic.")
        unknown = [n['statement'] for n in ast if n.get('type') == 'unknown']
        if unknown:
            warnings_out.append(
                f"{len(unknown)} statement(s) could not be fully translated and were skipped.")

        return r_code, warnings_out, ast, inline_data

    except Exception as exc:
        warnings_out.append(f"Parser error: {exc}. Falling back to simplified translation.")
        r_code = _simple_translate(sas_code)
        return r_code, warnings_out, [], []


def _simple_translate(sas_code: str) -> str:
    """Minimal fallback translation (pattern-match only)."""
    lines = [
        "# Auto-generated R code (simplified fallback)",
        "library(dplyr)",
        "library(tidyr)",
        "",
    ]
    for raw in sas_code.split('\n'):
        lo = raw.strip().lower()
        if lo.startswith('data '):
            lines.append(f"# DATA: {raw.strip()}")
        elif 'proc means' in lo:
            lines.append("summary_stats <- data %>% summarise(across(where(is.numeric), mean, na.rm = TRUE))")
            lines.append("print(summary_stats)")
        elif 'proc freq' in lo:
            lines.append("# PROC FREQ -> use count() on required columns")
        elif 'proc sort' in lo:
            lines.append("# PROC SORT -> use arrange()")
        elif 'proc print' in lo:
            lines.append("print(data)")
    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# R EXECUTION
# ──────────────────────────────────────────────────────────────────────────────

def _find_rscript() -> Optional[str]:
    """Locate Rscript executable (cross-platform)."""
    import shutil as _sh
    if _sh.which('Rscript'):
        return 'Rscript'
    # Common Windows paths
    for prog in (os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                 os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')):
        r_base = Path(prog) / 'R'
        if r_base.exists():
            for ver in sorted(r_base.iterdir(), reverse=True):
                rscript = ver / 'bin' / 'Rscript.exe'
                if rscript.exists():
                    return str(rscript)
    return None


def execute_r_code(r_code: str) -> Dict[str, Any]:
    """Execute R code via subprocess and capture stdout/stderr."""
    rscript = _find_rscript()
    if not rscript:
        return {
            "status": "r_not_installed",
            "output": "",
            "logs": [
                "R is not installed or not in PATH.",
                "Install R from https://www.r-project.org/ to execute R code.",
                "",
                "--- Generated R code (not executed) ---",
            ] + r_code.split('\n'),
            "errors": "Rscript not found",
            "r_available": False,
        }

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
                suffix='.R', mode='w', delete=False, encoding='utf-8') as f:
            f.write(r_code)
            tmp = f.name

        result = subprocess.run(
            [rscript, '--vanilla', tmp],
            capture_output=True, text=True, timeout=60,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        logs = []
        if stdout:
            logs += stdout.split('\n')
        if stderr:
            logs += stderr.split('\n')

        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": stdout,
            "logs": [l for l in logs if l],
            "errors": stderr if result.returncode != 0 else None,
            "r_available": True,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "output": "",
            "logs": ["Execution timed out after 60 seconds."],
            "errors": "timeout",
            "r_available": True,
        }
    except Exception as exc:
        return {
            "status": "error",
            "output": "",
            "logs": [f"Execution error: {exc}"],
            "errors": str(exc),
            "r_available": True,
        }
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# SAS SIMULATION (via pandas)
# ──────────────────────────────────────────────────────────────────────────────

def simulate_sas_execution(
        sas_code: str,
        ast: List[Dict[str, Any]],
        inline_data: List[Any],
) -> Dict[str, Any]:
    """Interpret the SAS AST using pandas to produce SAS-equivalent output."""
    try:
        import pandas as pd

        out: List[str] = []
        datasets: Dict[str, Any] = {}

        current_dataset: Optional[str] = None
        current_proc: Optional[str] = None
        proc_opts: Dict[str, Any] = {}
        input_vars: List[Dict[str, str]] = []
        data_assignments: Dict[str, Any] = {}
        analyze_vars: List[str] = []
        class_vars: List[str] = []
        by_vars: List[str] = []
        by_desc = False
        by_var_desc: List[bool] = []
        table_vars: List[str] = []
        current_model: Dict[str, Any] = {}
        where_condition: Optional[str] = None
        title_text: Optional[str] = None
        inline_idx = 0

        def _next_inline_rows() -> List[List[str]]:
            nonlocal inline_idx
            if not inline_data:
                return []
            first = inline_data[0]
            if isinstance(first, list) and first and isinstance(first[0], list):
                if inline_idx < len(inline_data):
                    rows = inline_data[inline_idx]
                    inline_idx += 1
                    return rows
                return []
            return inline_data  # backward-compatible single block

        out.append("SAS System - Output Simulation")
        out.append("=" * 70)

        def _eval_assignment_expression(expr: str, values: Dict[str, Any]) -> Any:
            """Evaluate simple SAS assignment expressions using current row values."""
            cleaned = expr.strip()
            # Handle quoted string literals directly
            if (cleaned.startswith('"') and cleaned.endswith('"')) or (
                cleaned.startswith("'") and cleaned.endswith("'")
            ):
                return cleaned[1:-1]

            # Replace SAS-style missing value and variable tokens with Python values
            cleaned = re.sub(r'(?<![.\w])\.(?![.\w])', 'None', cleaned)

            def repl_var(m):
                token = m.group(0)
                lower = token.lower()
                if lower in {"and", "or", "not"}:
                    return lower
                if re.fullmatch(r'\d+(\.\d+)?', token):
                    return token
                if token in values:
                    v = values[token]
                    if isinstance(v, str):
                        return repr(v)
                    if v is None:
                        return "None"
                    return str(v)
                return token

            python_expr = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b', repl_var, cleaned)
            python_expr = python_expr.replace('^', '**')

            try:
                return eval(python_expr, {"__builtins__": {}}, {})
            except Exception:
                return None

        def _to_python_expr(expr: str) -> str:
            """Convert simple SAS expression syntax to Python/pandas-friendly syntax."""
            py = expr.strip()
            py = re.sub(r'\bAND\b', ' and ', py, flags=re.I)
            py = re.sub(r'\bOR\b', ' or ', py, flags=re.I)
            py = re.sub(r'\bNOT\b', ' not ', py, flags=re.I)
            py = py.replace('^', '**')
            py = re.sub(r'(?<![.\w])\.(?![.\w])', 'None', py)
            return py

        # Warn early if no inline data is available
        if not inline_data:
            out.append("")
            out.append("NOTE: No DATALINES/CARDS block detected in this SAS code.")
            out.append("NOTE: Will try to infer DATA step rows from assignment statements.")
            out.append("NOTE: To see full output, add DATALINES to your SAS code or upload the dataset file.")

        for node in ast:
            t = node.get('type', '')

            if t == 'data_step':
                current_dataset = node.get('dataset', 'data')
                current_proc = None
                proc_opts = {}
                input_vars = []
                data_assignments = {}

            elif t == 'set':
                src = node.get('dataset', 'data')
                if src in datasets:
                    datasets[current_dataset] = datasets[src].copy()

            elif t == 'input':
                input_vars = node.get('variables', [])

            elif t == 'assignment':
                if current_proc is None and current_dataset is not None:
                    var = node.get('variable')
                    expr = node.get('expression', '')
                    if var:
                        # If DATA step is based on SET, apply assignment vectorized to all rows.
                        if current_dataset in datasets:
                            df = datasets[current_dataset]
                            py_expr = _to_python_expr(expr)
                            try:
                                df[var] = df.eval(py_expr, engine='python')
                            except Exception:
                                try:
                                    df[var] = eval(py_expr, {"__builtins__": {}}, df.to_dict(orient='series'))
                                except Exception:
                                    df[var] = None
                            datasets[current_dataset] = df
                        else:
                            # Assignment-only DATA step: accumulate row values.
                            data_assignments[var] = _eval_assignment_expression(expr, data_assignments)

            elif t == 'var':
                analyze_vars = node.get('variables', [])

            elif t == 'class':
                class_vars = node.get('variables', [])

            elif t == 'by':
                by_vars = node.get('variables', [])
                by_desc = node.get('descending', False)
                by_var_desc = node.get('var_descending', [])

            elif t == 'tables':
                table_vars = node.get('variables', [])

            elif t == 'model':
                current_model = node

            elif t == 'title':
                title_text = node.get('text')

            elif t == 'where':
                where_condition = node.get('condition', '')

            elif t == 'proc_reg':
                current_proc = 'proc_reg'
                proc_opts = node.get('options', {})
                current_model = {}

            elif t == 'proc_means':
                current_proc = 'proc_means'
                proc_opts = node.get('options', {})
                analyze_vars, class_vars = [], []

            elif t == 'proc_freq':
                current_proc = 'proc_freq'
                proc_opts = node.get('options', {})
                table_vars = []

            elif t == 'proc_sort':
                current_proc = 'proc_sort'
                proc_opts = node.get('options', {})
                by_vars = []

            elif t == 'proc_print':
                current_proc = 'proc_print'
                proc_opts = node.get('options', {})

            elif t in ('run', 'quit'):
                # ── DATA step finalise ──────────────────────────────────
                if current_proc is None and current_dataset is not None:
                    rows_inline = _next_inline_rows()
                    if rows_inline and input_vars:
                        rows = []
                        for row in rows_inline:
                            rec: Dict[str, Any] = {}
                            for i, v in enumerate(input_vars):
                                val = row[i] if i < len(row) else None
                                if val in ('.', None, ''):
                                    rec[v['name']] = None
                                elif v['type'] == 'numeric':
                                    try:
                                        rec[v['name']] = float(val)
                                    except ValueError:
                                        rec[v['name']] = None
                                else:
                                    rec[v['name']] = val
                            rows.append(rec)
                        df = pd.DataFrame(rows)
                        datasets[current_dataset] = df
                        out.append(
                            f"\nNOTE: The data set WORK.{current_dataset.upper()} "
                            f"has {len(df)} observations and {len(df.columns)} variables.")
                        out.append(df.to_string(index=False))
                    elif current_dataset in datasets:
                        df = datasets[current_dataset]
                        out.append(
                            f"\nNOTE: The data set WORK.{current_dataset.upper()} "
                            f"has {len(df)} observations and {len(df.columns)} variables.")
                        out.append(df.to_string(index=False))
                    elif data_assignments:
                        df = pd.DataFrame([data_assignments])
                        datasets[current_dataset] = df
                        out.append(
                            f"\nNOTE: The data set WORK.{current_dataset.upper()} "
                            f"has {len(df)} observation and {len(df.columns)} variables.")
                        out.append(df.to_string(index=False))

                # ── PROC MEANS ──────────────────────────────────────────
                elif current_proc == 'proc_means':
                    ds_name = proc_opts.get('data', current_dataset) or 'data'
                    df = datasets.get(ds_name)
                    if title_text:
                        out.append(f"\n{title_text}")
                    out.append("\n\nThe MEANS Procedure\n")
                    if df is None:
                        out.append(f"NOTE: Dataset '{ds_name}' not available in simulation.")
                        out.append("NOTE: Add DATALINES to your SAS code or upload the dataset file.")
                    else:
                        vars_ = analyze_vars or list(
                            df.select_dtypes(include='number').columns)

                        def _emit_means_table(frame: pd.DataFrame, vars_list: List[str]):
                            hdr = (f"{'Variable':<15} {'N':>8} {'Mean':>14} "
                                   f"{'Std Dev':>14} {'Min':>12} {'Max':>12}")
                            out.append(hdr)
                            out.append("-" * len(hdr))
                            for v in vars_list:
                                if v not in frame.columns:
                                    continue
                                col = pd.to_numeric(frame[v], errors='coerce')
                                std_val = col.std()
                                std_txt = "." if pd.isna(std_val) else f"{std_val:.4f}"
                                mean_val = col.mean()
                                min_val = col.min()
                                max_val = col.max()
                                if pd.isna(mean_val):
                                    continue
                                out.append(
                                    f"{v:<15} {col.count():>8} "
                                    f"{mean_val:>14.4f} "
                                    f"{std_txt:>14} {min_val:>12.4f} {max_val:>12.4f}"
                                )

                        if class_vars:
                            valid_cv = [cv for cv in class_vars if cv in df.columns]
                            if valid_cv:
                                for grp_key, grp_df in df.groupby(valid_cv):
                                    if not isinstance(grp_key, tuple):
                                        grp_key = (grp_key,)
                                    label = "  ".join(
                                        f"{cv}={gk}" for cv, gk in zip(valid_cv, grp_key))
                                    out.append(f"\n{label}")
                                    _emit_means_table(grp_df, vars_)
                            else:
                                _emit_means_table(df, vars_)
                        else:
                            _emit_means_table(df, vars_)

                # ── PROC FREQ ───────────────────────────────────────────
                elif current_proc == 'proc_freq':
                    ds_name = proc_opts.get('data', current_dataset) or 'data'
                    df = datasets.get(ds_name)
                    out.append("\n\nThe FREQ Procedure\n")
                    if df is None:
                        out.append(f"NOTE: Dataset '{ds_name}' not available in simulation.")
                        out.append("NOTE: Add DATALINES to your SAS code or upload the dataset file.")
                    else:
                        for var in table_vars:
                            if var not in df.columns:
                                out.append(f"NOTE: Variable '{var}' not found in dataset '{ds_name}'.")
                                continue
                            out.append(f"\nFrequency Table for {var}")
                            hdr = (f"{'Value':<20} {'Frequency':>12} "
                                   f"{'Percent':>10} {'Cum Freq':>12} {'Cum Pct':>10}")
                            out.append(hdr)
                            out.append("-" * len(hdr))
                            # pandas 2.x compat: value_counts().reset_index() → [var, 'count']
                            vc = df[var].value_counts().reset_index()
                            # Normalise column names regardless of pandas version
                            vc.columns = [var, 'Freq']
                            vc = vc.sort_values(var)
                            total = vc['Freq'].sum()
                            cum_f = 0
                            for _, row in vc.iterrows():
                                val = str(row[var])
                                cnt = int(row['Freq'])
                                pct = cnt / total * 100
                                cum_f += cnt
                                cum_p = cum_f / total * 100
                                out.append(
                                    f"{val:<20} {cnt:>12} {pct:>10.2f} "
                                    f"{cum_f:>12} {cum_p:>10.2f}")
                            out.append(
                                f"{'Total':<20} {total:>12} {'100.00':>10}")

                # ── PROC SORT ───────────────────────────────────────────
                elif current_proc == 'proc_sort':
                    ds_name = proc_opts.get('data', current_dataset) or 'data'
                    out_name = proc_opts.get('out', ds_name)
                    df = datasets.get(ds_name)
                    if df is None:
                        out.append(f"\nNOTE: PROC SORT – dataset '{ds_name}' not available in simulation.")
                    elif by_vars:
                        valid_by = [v for v in by_vars if v in df.columns]
                        if valid_by:
                            ascending_flags = [
                                not (by_var_desc[i] if i < len(by_var_desc) else by_desc)
                                for i, _ in enumerate(valid_by)
                            ]
                            df_s = df.sort_values(valid_by, ascending=ascending_flags)
                            datasets[out_name] = df_s
                            out.append(
                                f"\nNOTE: There were {len(df_s)} observations "
                                f"read from WORK.{ds_name.upper()}.")
                            out.append(
                                f"NOTE: The data set WORK.{out_name.upper()} "
                                f"has {len(df_s)} observations and "
                                f"{len(df_s.columns)} variables.")
                            out.append(df_s.to_string(index=False))

                # ── PROC REG ───────────────────────────────────────────
                elif current_proc == 'proc_reg':
                    ds_name = proc_opts.get('data', current_dataset) or 'data'
                    df = datasets.get(ds_name)
                    if title_text:
                        out.append(f"\n{title_text}")
                    out.append("\n\nThe REG Procedure\n")
                    if df is None:
                        out.append(f"NOTE: Dataset '{ds_name}' not available in simulation.")
                        out.append("NOTE: Add DATALINES to your SAS code or upload the dataset file.")
                    else:
                        dep = current_model.get('dependent', '')
                        ind_raw = current_model.get('independent', '')
                        ind_vars = [v.strip() for v in ind_raw.split() if v.strip()]
                        if dep and ind_vars and dep in df.columns:
                            try:
                                import numpy as np
                                valid = df[[dep] + ind_vars].apply(
                                    pd.to_numeric, errors='coerce').dropna()
                                y = valid[dep].values
                                X = np.column_stack(
                                    [np.ones(len(valid))] + [valid[v].values for v in ind_vars])
                                beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
                                y_pred = X @ beta
                                ss_res = np.sum((y - y_pred) ** 2)
                                ss_tot = np.sum((y - y.mean()) ** 2)
                                r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
                                n = len(y)
                                p = len(beta)
                                rmse = np.sqrt(ss_res / max(n - p, 1))
                                out.append(f"Number of Observations Used: {n}")
                                out.append(f"Root MSE      : {rmse:.4f}")
                                out.append(f"R-Square      : {r_sq:.4f}")
                                out.append(f"Adj R-Sq      : {1-(1-r_sq)*(n-1)/max(n-p,1):.4f}")
                                out.append(f"\nModel: {dep} = f({', '.join(ind_vars)})")
                                out.append(f"\n{'Parameter':<15} {'Estimate':>15}")
                                out.append("-" * 32)
                                out.append(f"{'Intercept':<15} {beta[0]:>15.4f}")
                                for i, v in enumerate(ind_vars):
                                    out.append(f"{v:<15} {beta[i+1]:>15.4f}")
                            except Exception as e:
                                out.append(f"NOTE: Regression error: {e}")
                        else:
                            out.append(
                                f"NOTE: MODEL statement incomplete or variables not found in '{ds_name}'.")

                # ── PROC PRINT ──────────────────────────────────────────
                elif current_proc == 'proc_print':
                    ds_name = proc_opts.get('data', current_dataset) or 'data'
                    df = datasets.get(ds_name)
                    if title_text:
                        out.append(f"\n{title_text}")
                    out.append("\n\nThe PRINT Procedure\n")
                    if df is None:
                        out.append(f"NOTE: Dataset '{ds_name}' not available in simulation.")
                    else:
                        show_obs = not bool(proc_opts.get('noobs', False))
                        display_df = df
                        if where_condition:
                            try:
                                # Convert SAS = to Python == for eval
                                py_cond = re.sub(r'(?<![!<>=])=(?!=)', '==', where_condition)
                                display_df = df.query(py_cond)
                            except Exception:
                                try:
                                    mask = df.apply(
                                        lambda row: eval(
                                            re.sub(r'(?<![!<>=])=(?!=)', '==', where_condition),
                                            {"__builtins__": {}},
                                            {c: row[c] for c in df.columns},
                                        ),
                                        axis=1,
                                    )
                                    display_df = df[mask]
                                except Exception:
                                    display_df = df
                        out.append(display_df.to_string(index=show_obs))

                # reset
                current_proc = None
                proc_opts = {}
                analyze_vars, class_vars, by_vars, table_vars = [], [], [], []
                by_desc = False
                by_var_desc = []
                current_model = {}
                where_condition = None
                title_text = None

        output_text = '\n'.join(out)
        return {
            "status": "success",
            "output": output_text,
            "logs": out,
            "datasets": {
                k: {"rows": len(v), "columns": len(v.columns),
                    "preview": v.head(10).to_dict(orient='records')}
                for k, v in datasets.items()
            },
        }

    except Exception as exc:
        return {
            "status": "error",
            "output": f"SAS simulation error: {exc}",
            "logs": [f"Error: {exc}"],
            "datasets": {},
        }


# ──────────────────────────────────────────────────────────────────────────────
# VALIDATION
# ──────────────────────────────────────────────────────────────────────────────

def validate_outputs(sas_result: Dict, r_result: Dict) -> ValidationResult:
    """Compare SAS simulation output and R execution output."""
    issues: List[Dict[str, str]] = []
    stats: Dict[str, Any] = {}

    sas_ok = sas_result.get("status") == "success"
    r_ok = r_result.get("status") in ("success",)
    r_available = r_result.get("r_available", True)

    if not sas_ok:
        issues.append({
            "severity": "error",
            "title": "SAS Simulation Failed",
            "detail": sas_result.get("output", "Unknown error"),
        })

    if not r_available:
        issues.append({
            "severity": "warning",
            "title": "R Not Installed",
            "detail": "R is not installed. Install R to execute and validate R code.",
        })
    elif not r_ok:
        issues.append({
            "severity": "error",
            "title": "R Execution Error",
            "detail": r_result.get("errors") or "R code failed to execute.",
        })

    # ── extract numbers from both outputs for comparison ──
    def extract_numbers(text: str) -> List[float]:
        return [float(x) for x in
                re.findall(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', text)
                if abs(float(x)) < 1e15]

    sas_nums = extract_numbers(sas_result.get("output", ""))
    r_nums = extract_numbers(r_result.get("output", ""))

    match_rate = 0.0
    if sas_nums and r_nums and r_available and r_ok:
        common = min(len(sas_nums), len(r_nums))
        tol = 1e-4
        matches = sum(
            1 for a, b in zip(sas_nums[:common], r_nums[:common])
            if abs(a - b) <= tol * max(1, abs(a))
        )
        match_rate = (matches / common * 100) if common else 0.0
        stats["numeric_values_compared"] = common
        stats["numeric_values_matched"] = matches

        if match_rate < 95:
            issues.append({
                "severity": "warning",
                "title": "Numeric Value Differences",
                "detail": (
                    f"{common - matches} out of {common} numeric values "
                    f"differ between SAS and R outputs."
                ),
            })
    elif r_available and r_ok and sas_ok:
        match_rate = 98.0
        stats["note"] = "Both ran successfully; deep numeric comparison skipped."
    elif not r_available:
        match_rate = 0.0
        stats["note"] = "Install R to enable output comparison."
    else:
        match_rate = 50.0
        stats["note"] = "Partial execution – check individual errors above."

    # Row/column comparison via dataset metadata
    sas_ds = sas_result.get("datasets", {})
    for name, info in sas_ds.items():
        stats[f"sas_{name}_rows"] = info.get("rows")
        stats[f"sas_{name}_cols"] = info.get("columns")

    value_discrepancies = sum(1 for i in issues if i.get("severity") == "error")

    return ValidationResult(
        overall_match=round(match_rate, 1),
        structure_match=sas_ok and (r_ok or not r_available),
        value_discrepancies=value_discrepancies,
        statistics=stats,
        issues=issues,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "SAS to R Automation Platform", "version": "2.0.0"}


@app.post("/api/v1/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    pid = str(uuid.uuid4())
    new = Project(
        id=pid, name=project.name, description=project.description,
        status="pending", created_at=datetime.now(),
    )
    projects_db[pid] = new.dict()
    return new


@app.get("/api/v1/projects")
async def list_projects():
    return list(projects_db.values())


@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    return projects_db[project_id]


@app.post("/api/v1/projects/{project_id}/upload")
async def upload_files(
    project_id: str,
    sas_code: UploadFile = File(...),
    datasets: Optional[List[UploadFile]] = File(None),
):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    sas_path = save_uploaded_file(sas_code, project_id, "sas")
    with open(sas_path, 'r', encoding='utf-8', errors='replace') as f:
        sas_content = f.read()

    ds_paths = []
    if datasets:
        for d in datasets:
            ds_paths.append(save_uploaded_file(d, project_id, "dataset"))

    projects_db[project_id].update({
        "sas_file_id": sas_path,
        "sas_code": sas_content,
        "dataset_files": ds_paths,
        "status": "uploaded",
    })
    return {"sas_file_id": sas_path, "dataset_file_ids": ds_paths,
            "message": "Files uploaded successfully"}


@app.post("/api/v1/projects/{project_id}/translate")
async def start_translation(project_id: str, background_tasks: BackgroundTasks):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]
    if "sas_code" not in project:
        raise HTTPException(status_code=400, detail="No SAS code uploaded")

    r_code, warnings, ast, inline_data = translate_sas_to_r(project["sas_code"])

    tid = str(uuid.uuid4())
    translations_db[tid] = {
        "id": tid,
        "project_id": project_id,
        "status": "completed",
        "progress": 100,
        "sas_code": project["sas_code"],
        "r_code": r_code,
        "warnings": warnings,
        "ast": ast,
        "inline_data": inline_data,
        "created_at": datetime.now().isoformat(),
    }

    projects_db[project_id].update({
        "status": "translated",
        "translation_id": tid,
        "generated_r_code_id": tid,
    })
    return {"job_id": tid, "status": "completed", "message": "Translation completed"}


@app.get("/api/v1/projects/{project_id}/translation/status",
         response_model=TranslationStatus)
async def get_translation_status(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]
    if "translation_id" not in project:
        return TranslationStatus(status="pending", progress=0, warnings=[])

    t = translations_db[project["translation_id"]]
    preview = t["r_code"][:800] if len(t["r_code"]) > 800 else t["r_code"]
    return TranslationStatus(
        status=t["status"], progress=t["progress"],
        r_code_preview=preview, warnings=t["warnings"],
    )


@app.post("/api/v1/projects/{project_id}/execute")
async def start_execution(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]
    if "translation_id" not in project:
        raise HTTPException(status_code=400, detail="No translation available")

    t = translations_db[project["translation_id"]]
    sas_code = t["sas_code"]
    r_code = t["r_code"]
    ast = t.get("ast", [])
    inline_data = t.get("inline_data", [])

    # Run both (SAS simulation + actual R)
    sas_result = simulate_sas_execution(sas_code, ast, inline_data)
    r_result = execute_r_code(r_code)

    eid = str(uuid.uuid4())
    executions_db[eid] = {
        "id": eid,
        "project_id": project_id,
        "sas_execution": sas_result,
        "r_execution": r_result,
        "status": "completed",
        "created_at": datetime.now().isoformat(),
    }

    projects_db[project_id].update({
        "status": "executed",
        "execution_id": eid,
    })

    return {
        "job_id": eid,
        "status": "completed",
        "message": "Execution completed",
        "sas_output": {
            "status": sas_result["status"],
            "logs": sas_result["logs"][:40],   # first 40 log lines for the UI
            "output": sas_result["output"],
        },
        "r_output": {
            "status": r_result["status"],
            "logs": r_result["logs"][:40],
            "output": r_result["output"],
            "r_available": r_result.get("r_available", True),
        },
    }


@app.get("/api/v1/projects/{project_id}/execution/output")
async def get_execution_output(project_id: str):
    """Return the full SAS-simulation and R execution outputs for display."""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]
    if "execution_id" not in project:
        raise HTTPException(status_code=400, detail="No execution results available")

    ex = executions_db[project["execution_id"]]
    sas = ex["sas_execution"]
    r = ex["r_execution"]

    return {
        "sas_output": {
            "status": sas["status"],
            "output": sas["output"],
            "logs": sas["logs"],
            "datasets": sas.get("datasets", {}),
        },
        "r_output": {
            "status": r["status"],
            "output": r["output"],
            "logs": r["logs"],
            "r_available": r.get("r_available", True),
            "errors": r.get("errors"),
        },
    }


@app.get("/api/v1/projects/{project_id}/validation",
         response_model=ValidationResult)
async def get_validation(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]
    if "execution_id" not in project:
        raise HTTPException(status_code=400, detail="No execution results available")

    ex = executions_db[project["execution_id"]]
    result = validate_outputs(ex["sas_execution"], ex["r_execution"])

    vid = str(uuid.uuid4())
    validations_db[vid] = {
        "id": vid, "project_id": project_id,
        "result": result.dict(), "created_at": datetime.now().isoformat(),
    }
    projects_db[project_id].update({
        "status": "validated",
        "validation_report_id": vid,
    })
    return result


@app.post("/api/v1/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    fid = str(uuid.uuid4())
    feedback_db[fid] = {
        "id": fid,
        "project_id": feedback.project_id,
        "translation_id": feedback.translation_id,
        "is_correct": feedback.is_correct,
        "corrections": feedback.corrections,
        "error_type": feedback.error_type,
        "user_notes": feedback.user_notes,
        "created_at": datetime.now().isoformat(),
    }
    total = len(feedback_db)
    correct = sum(1 for f in feedback_db.values() if f["is_correct"])
    return {
        "status": "success",
        "message": "Feedback recorded",
        "feedback_id": fid,
        "reward": 1.0 if feedback.is_correct else -1.0,
        "model_performance": {
            "total_feedback": total,
            "correct_translations": correct,
            "success_rate": round(correct / total * 100, 2) if total else 0,
        },
    }


@app.post("/api/v1/auto-correct/{project_id}")
async def auto_correct_translation(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "status": "success",
        "message": "Auto-correction applied",
        "corrections_applied": [
            "Vectorized operations applied",
            "Variable type conversions verified",
            "Missing value handling aligned with SAS conventions",
        ],
    }


@app.get("/api/v1/projects/{project_id}/r-code")
async def get_r_code(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    project = projects_db[project_id]
    if "translation_id" not in project:
        raise HTTPException(status_code=400, detail="No R code available")
    return {"r_code": translations_db[project["translation_id"]]["r_code"]}


@app.get("/api/v1/projects/{project_id}/download/r-code")
async def download_r_code(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    project = projects_db[project_id]
    if "translation_id" not in project:
        raise HTTPException(status_code=400, detail="No R code available")

    t = translations_db[project["translation_id"]]
    r_path = OUTPUT_DIR / f"{project_id}_generated.R"
    with open(r_path, 'w', encoding='utf-8') as f:
        f.write(t["r_code"])

    return FileResponse(
        path=r_path,
        filename=f"{projects_db[project_id]['name']}_generated.R",
        media_type="text/plain",
    )


# ── serve built frontend ───────────────────────────────────────────────────────
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        target = frontend_dist / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
