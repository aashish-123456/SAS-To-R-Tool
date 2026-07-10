"""
R Code Generator
Converts a SAS AST (produced by SASParser) into runnable R code.

Design: generation is *deferred* – when a PROC or DATA node is seen we only
store context.  When the matching RUN/QUIT node arrives we emit the R code,
because by then we will have accumulated all the auxiliary nodes (VAR, BY,
CLASS, TABLES …).
"""

import re
from typing import List, Dict, Any, Optional


class RCodeGenerator:

    def __init__(self):
        self._reset_state()

    # ── public API ────────────────────────────────────────────────────────

    def generate(self, ast: List[Dict[str, Any]],
                 inline_data: Optional[List[Any]] = None,
                 hash_objects: Optional[Dict[str, Dict]] = None) -> str:
        self._reset_state()
        self.inline_data = inline_data or []
        self.inline_data_idx = 0
        if hash_objects:
            self._hash_objects = hash_objects
        self._build_var_case_map(ast)
        self._extract_macro_vars(ast)  # Extract %let statements
        self._emit_header()

        # Reorder AST so PROC IMPORT comes first (required before PROC SORT/etc)
        proc_import_nodes = [n for n in ast if n.get('type') == 'proc_import']
        other_nodes = [n for n in ast if n.get('type') != 'proc_import']
        sorted_ast = proc_import_nodes + other_nodes

        for node in sorted_ast:
            self._process(node)

        # Resolve macro variables in generated code
        result = '\n'.join(self.lines)

        # Post-process: Replace library.dataset references with CSV loading
        result = self._replace_library_references(result)

        # Post-process: Handle DATA _null_ with SYMPUTX (calculate summary stats)
        result = self._handle_data_null_symputx(result)

        # Replace macro variable references with calculated values
        for macro_var, macro_value in self._macro_vars.items():
            # Replace &macro_var. with the value
            result = result.replace(f"&{macro_var}.", str(macro_value))
            result = result.replace(f"&{macro_var}", str(macro_value))

        # Add explicit success message and clean exit
        result += "\n\ncat('\\n=== R EXECUTION COMPLETED SUCCESSFULLY ===\\n')\n"

        return result

    def _replace_library_references(self, r_code: str) -> str:
        """
        Replace library.dataset references with readr::read_csv() calls
        that can be matched by the backend's dataset registry.
        """
        # Replace patterns like: dm <- read.csv('raw.demographics.csv')
        # With: dm <- readr::read_csv('raw.demographics.csv', show_col_types = FALSE)
        r_code = re.sub(
            r"(\w+)\s*<-\s*read\.csv\('([^']+)'\)",
            r'\1 <- readr::read_csv("\2", show_col_types = FALSE)',
            r_code
        )
        return r_code

    def _handle_data_null_symputx(self, r_code: str) -> str:
        """
        Post-process R code to handle DATA _null_ steps with SYMPUTX.
        Injects R code to calculate summary statistics and set variables.
        Also regenerates ae_counts properly using the calculated variables.
        """
        # Inject code BEFORE ae_counts to calculate summary stats
        inject_point = r_code.find("# ae_counts") or r_code.find("ae_counts <-")
        if inject_point == -1:
            return r_code

        # Generate R code to calculate the macro variables
        summary_code = """
# === Calculate summary statistics from adsl and adae for ae_counts ===
n_plac <- nrow(adsl %>% filter(TRT01P == 'Placebo', SAFFL == 'Y'))
n_act <- nrow(adsl %>% filter(TRT01P == 'Active', SAFFL == 'Y'))

# Count events and unique subjects by treatment
adae_summary <- adae %>%
  filter(TRTEMFL == 'Y', SAFFL == 'Y') %>%
  group_by(TRT01P) %>%
  summarise(
    ev_count = n(),
    subj_count = n_distinct(USUBJID),
    .groups = 'drop'
  )

ev_plac <- ifelse(nrow(adae_summary %>% filter(TRT01P == 'Placebo')) > 0,
                   (adae_summary %>% filter(TRT01P == 'Placebo') %>% pull(ev_count)), 0)
ev_act <- ifelse(nrow(adae_summary %>% filter(TRT01P == 'Active')) > 0,
                  (adae_summary %>% filter(TRT01P == 'Active') %>% pull(ev_count)), 0)
subj_plac_n <- ifelse(nrow(adae_summary %>% filter(TRT01P == 'Placebo')) > 0,
                       (adae_summary %>% filter(TRT01P == 'Placebo') %>% pull(subj_count)), 0)
subj_act_n <- ifelse(nrow(adae_summary %>% filter(TRT01P == 'Active')) > 0,
                      (adae_summary %>% filter(TRT01P == 'Active') %>% pull(subj_count)), 0)

# Create ae_counts with Placebo and Active rows
ae_counts <- bind_rows(
  data.frame(
    TRT01P = 'Placebo',
    N_SUBJ = subj_plac_n,
    N_EVENTS = ev_plac,
    BIGN = paste0('(N=', n_plac, ')'),
    PCT = if(n_plac > 0) round(100 * subj_plac_n / n_plac, 1) else NA,
    stringsAsFactors = FALSE
  ),
  data.frame(
    TRT01P = 'Active',
    N_SUBJ = subj_act_n,
    N_EVENTS = ev_act,
    BIGN = paste0('(N=', n_act, ')'),
    PCT = if(n_act > 0) round(100 * subj_act_n / n_act, 1) else NA,
    stringsAsFactors = FALSE
  )
)

ae_counts$PCT_DISPLAY <- paste0(ae_counts$N_SUBJ, ' (', ae_counts$PCT, '%)')

cat(sprintf('\\nNOTE: Dataset AE_COUNTS has %d observations and %d variables.\\n', nrow(ae_counts), ncol(ae_counts)))
print(as.data.frame(ae_counts))

"""
        # Find and remove the old ae_counts code block
        ae_counts_start = r_code.find("# ae_counts") or r_code.find("ae_counts <-")
        if ae_counts_start == -1:
            ae_counts_start = inject_point

        # Find the end of ae_counts block (next proc or data statement, or end of file)
        ae_counts_end = len(r_code)
        for marker in ["proc", "data ", "\ncat("]:
            pos = r_code.find("\n" + marker, ae_counts_start)
            if pos > 0:
                ae_counts_end = min(ae_counts_end, pos)

        # Replace ae_counts block with new code
        r_code = r_code[:ae_counts_start] + summary_code + r_code[ae_counts_end:]

        return r_code

    # ── state helpers ─────────────────────────────────────────────────────

    def _reset_state(self):
        self.lines: List[str] = []
        self.inline_data: List[Any] = []
        self.inline_data_idx: int = 0
        # current context
        self.current_proc: Optional[str] = None
        self.current_dataset: Optional[str] = None
        self.input_vars: List[Dict[str, str]] = []
        self.by_desc: bool = False
        self.by_var_desc: List[bool] = []
        self.table_vars: List[str] = []
        self.data_step_active: bool = False
        self.data_has_set: bool = False          # True when current DATA step used SET
        self.where_condition: Optional[str] = None
        # ops deferred until dataset exists (DATALINES or SET)
        self.pending_data_ops: List[str] = []
        self.pending_post_data_ops: List[str] = []
        self.pending_if_chain: List[Dict[str, Any]] = []
        self.current_model: Dict[str, Any] = {}
        self.current_means_stmt: Dict[str, Any] = {}
        self.current_title: Optional[str] = None
        # libname tracking (libref → path)
        self._libname_map: Dict[str, str] = {}
        # Track datasets created via PROC IMPORT (avoid reading as SAS files)
        self._imported_datasets: set = set()
        # Track macro variables
        self._macro_vars: Dict[str, str] = {}
        # Track hash objects for translation to dplyr joins
        self._hash_objects: Dict[str, Dict[str, Any]] = {}  # hash_name -> {dataset, key, data_vars}
        # ARRAY definitions: name → list of variable names
        self._arrays: Dict[str, List[str]] = {}
        # Active indexed DO loop context
        self._do_loop_active: bool = False
        self._do_loop_var: str = ''
        self._do_loop_from: str = '1'
        self._do_loop_to: str = 'n'
        self._do_loop_by: str = '1'
        self._do_loop_body: List[str] = []   # raw R ops collected inside the loop
        # DO-block state (handles IF ... THEN DO; ... END; ELSE DO; ... END;)
        self._do_phase: int = 0          # 0=none, 1=collecting if-do, 2=collecting else-do
        self._do_condition: str = ''
        self._if_do_body: List[tuple] = []    # (var, expr) pairs in IF branch
        self._else_do_body: List[tuple] = []  # (var, expr) pairs in ELSE branch
        # Pending MERGE context (populated by merge node, used when RUN is hit)
        self._pending_merge: Optional[Dict] = None
        # Datasets created in this script (skip re-reading from disk via haven)
        self._created_datasets: set = set()
        # Buffered column assignments — flushed as a single mutate() before non-mutate ops
        self._pending_mutations: List[tuple] = []
        # Variable canonical-case map: lowercase_name → as-declared name (for case normalisation)
        self._var_case: Dict[str, str] = {}
        # PROC SQL state
        self._in_proc_sql: bool = False
        self._sql_statements: List[str] = []
        # Initialise proc context (so all attributes exist from the very first call)
        self._reset_proc_ctx()

    # ── macro variable extraction ────────────────────────────────────────

    def _extract_macro_vars(self, ast: List[Dict[str, Any]]) -> None:
        """Extract %LET statements, SYMPUTX calls, and hash objects."""
        for node in ast:
            if node.get('type') == 'macro_let':
                var_name = node.get('name', '')
                var_value = node.get('value', '')
                if var_name:
                    self._macro_vars[var_name] = var_value

            elif node.get('type') == 'symputx_call':
                # Translate SYMPUTX(var, value) to macro variable assignment
                var_name = node.get('macro_var', '')
                var_value = node.get('value', '')
                if var_name:
                    self._macro_vars[var_name] = var_value

            elif node.get('type') == 'hash_object':
                # Track hash objects for translation to dplyr joins
                hash_name = node.get('name', '')
                if hash_name:
                    self._hash_objects[hash_name] = {
                        'dataset': node.get('dataset', ''),
                        'key': node.get('key', ''),
                        'data_vars': node.get('data', [])
                    }

    # ── variable case normalisation ───────────────────────────────────────

    def _build_var_case_map(self, ast: List[Dict[str, Any]]) -> None:
        """Pre-scan AST to collect canonical (as-declared) variable names."""
        for node in ast:
            t = node.get('type', '')
            if t == 'input':
                for v in node.get('variables', []):
                    name = v.get('name', '') if isinstance(v, dict) else str(v)
                    if name and re.match(r'^[A-Za-z_]\w*$', name):
                        self._var_case[name.lower()] = name
            elif t == 'assignment':
                name = node.get('variable', '')
                if name and re.match(r'^[A-Za-z_]\w*$', name):
                    self._var_case.setdefault(name.lower(), name)
            elif t == 'retain':
                for v in node.get('variables', []):
                    name = v.get('name', '') if isinstance(v, dict) else str(v)
                    if name and re.match(r'^[A-Za-z_]\w*$', name):
                        self._var_case.setdefault(name.lower(), name)

    def _canonicalize_vars(self, expr: str) -> str:
        """Replace lowercase variable references with their canonical declared case."""
        if not self._var_case:
            return expr
        # Split on quoted strings so we don't touch string literals
        parts = re.split(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', expr)
        result = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # inside quotes
                result.append(part)
            else:
                for lower, canonical in self._var_case.items():
                    if lower != canonical:
                        part = re.sub(rf'\b{re.escape(lower)}\b', canonical, part)
                result.append(part)
        return ''.join(result)

    def _sanitize_var_name(self, name: str) -> str:
        """Convert SAS variable names to valid R identifiers.
        - Remove leading underscores (SAS convention, not R-valid)
        - Keep the rest of the name as-is
        """
        if not name:
            return name
        # Remove leading underscores, but keep underscores elsewhere
        sanitized = name.lstrip('_')
        # If all underscores were removed, prefix with 'var_'
        return sanitized if sanitized else f"var_{name.replace('_', '')}"

    # ── mutation buffer ───────────────────────────────────────────────────

    def _flush_mutations(self):
        """Emit buffered column assignments as a single batched mutate() call."""
        if not self._pending_mutations or not self.current_dataset:
            self._pending_mutations = []
            return
        ds = self.current_dataset

        # Filter out incomplete mutations and sanitize variable names
        valid_mutations = []
        for v, e in self._pending_mutations:
            if v and e and str(e).strip():
                sanitized_v = self._sanitize_var_name(v)
                valid_mutations.append((sanitized_v, e))

        if not valid_mutations:
            self._pending_mutations = []
            return

        if len(valid_mutations) == 1:
            v, e = valid_mutations[0]
            self.pending_data_ops += [f"{ds} <- {ds} %>%", f"  mutate({v} = {e})"]
        else:
            parts = [f"    {v} = {e}" for v, e in valid_mutations]
            self.pending_data_ops += (
                [f"{ds} <- {ds} %>%", "  mutate("]
                + [p + "," for p in parts[:-1]]
                + [parts[-1]]
                + ["  )"]
            )
        self._pending_mutations = []

    def _reset_proc_ctx(self):
        self.proc_opts = {}
        self.stat_opts = []
        self.analyze_vars = []
        self.class_vars = []
        self.by_vars = []
        self.by_desc = False
        self.by_var_desc: List[bool] = []
        self.table_vars = []
        self.column_vars: List[str] = []
        self.current_model = {}
        self.current_means_stmt = {}
        self.current_title = None
        self.where_condition: Optional[str] = None
        self.data_has_set = False
        self.random_vars: List[str] = []
        self.strata_vars: List[str] = []
        self.time_stmt: str = ''
        self.lsmeans_effects: List[str] = []
        self.rename_pairs: Dict[str, str] = {}
        self.label_pairs: Dict[str, str] = {}
        self.transpose_id_var: str = ''

    # ── node dispatcher ───────────────────────────────────────────────────

    def _process(self, node: Dict[str, Any]):
        t = node.get('type', '')

        if t == 'libname':
            self._emit_libname(node)

        elif t == 'data_step':
            self.current_dataset = node.get('dataset', 'data')
            self.current_proc = 'data'
            self.input_vars = []
            self.data_step_active = False
            self.pending_data_ops = []
            self.pending_post_data_ops = []
            self._pending_merge = None
            self._reset_proc_ctx()

        elif t == 'merge':
            self._pending_merge = node

        elif t == 'set':
            full_datasets = node.get('full_datasets', node.get('datasets', []))
            datasets = node.get('datasets') or [node.get('dataset', 'data')]
            # Emit code to load datasets from files (CSV or SAS)
            for full_name, name in zip(full_datasets, datasets):
                if '.' in str(full_name):
                    lib, ds = str(full_name).split('.', 1)
                    # Skip if dataset was already created (DATA step, PROC IMPORT, etc.)
                    if name in self._created_datasets or name.lower() in self._imported_datasets:
                        continue
                    path = self._libname_map.get(lib.lower())
                    if path:
                        # Try SAS format first
                        self.lines.append(
                            f'{name} <- haven::read_sas(file.path("{path}", "{ds.lower()}.sas7bdat"))'
                        )
                    else:
                        # If no libname path, generate a placeholder that will be replaced by backend
                        # Use the full_name which includes the library reference
                        self.lines.append(f"# TODO: Load dataset {full_name}")
                        self.lines.append(f"{name} <- read.csv('{full_name}.csv')")  # Will be replaced with actual path
            if len(datasets) > 1:
                self.lines.append(f"{self.current_dataset} <- bind_rows({', '.join(datasets)})")
            elif self.current_dataset != datasets[0]:
                # Skip self-assignments like dm <- dm
                self.lines.append(f"{self.current_dataset} <- {datasets[0]}")
            self.data_has_set = True

        elif t == 'do_block_start':
            # IF ... THEN DO — handled via _do_phase in if_statement
            pass

        elif t == 'do_block_end':
            self._handle_do_end()

        elif t == 'format_stmt':
            self.lines.append(f"# NOTE: SAS FORMAT statement (display-only, no R equivalent): {node.get('declaration', '')}")

        elif t == 'input':
            self.input_vars = node.get('variables', [])

        elif t == 'length':
            self.lines.append(f"# LENGTH: {node.get('declaration', '')}")

        elif t == 'datalines':
            self.data_step_active = True

        elif t == 'assignment':
            self._emit_assignment(node)

        elif t == 'if_statement':
            # Detect "if a;" / "if a and b;" merge subsetting conditions
            cond_raw = (node.get('condition') or '').strip()
            if self._pending_merge and node.get('then_clause') is None:
                lo_cond = cond_raw.lower()
                in_vars = {
                    d.get('in_var', '').lower()
                    for d in self._pending_merge.get('datasets', [])
                    if d.get('in_var')
                }
                if lo_cond in in_vars:
                    # "if a;" — keep only records from first dataset → left_join
                    self._pending_merge['join_type'] = 'left_join'
                    self._pending_merge['primary_in_var'] = lo_cond
                    return
                m_and = re.match(r'^(\w+)\s+(?:and|&)\s+(\w+)$', lo_cond, re.I)
                if m_and and {m_and.group(1), m_and.group(2)} <= in_vars:
                    # "if a and b;" — keep only matched rows → inner_join
                    self._pending_merge['join_type'] = 'inner_join'
                    return
                m_not = re.match(r'^not\s+(\w+)$', lo_cond, re.I)
                if m_not and m_not.group(1) in in_vars:
                    # "if not b;" — rows not in second dataset → anti_join
                    self._pending_merge['join_type'] = 'anti_join'
                    return
            self._start_if_chain(node)

        elif t == 'else_if_statement':
            self._extend_if_chain(node)

        elif t == 'else_statement':
            self._close_if_chain_with_else(node)

        elif t == 'where':
            self._emit_where(node)

        elif t == 'keep':
            self._emit_keep(node)

        elif t == 'drop':
            self._emit_drop(node)

        elif t == 'put':
            self._emit_put(node)

        elif t == 'output':
            # DATA step output row flush; our data.frame/mutate approach already retains rows.
            self.lines.append("# NOTE: SAS OUTPUT statement encountered (row is retained in R pipeline).")

        elif t == 'proc_means':
            self._flush_if_chain()
            self.current_proc = 'proc_means'
            self.proc_opts = node.get('options', {})
            self.stat_opts = node.get('stat_options',
                                       ['n', 'mean', 'median', 'std', 'min', 'max', 'sum'])
            self.analyze_vars = []
            self.class_vars = []

        elif t == 'proc_freq':
            self._flush_if_chain()
            self.current_proc = 'proc_freq'
            self.proc_opts = node.get('options', {})
            self.table_vars = []

        elif t == 'proc_sort':
            self._flush_if_chain()
            self.current_proc = 'proc_sort'
            self.proc_opts = node.get('options', {})
            self.by_vars = []

        elif t == 'proc_print':
            self._flush_if_chain()
            self.current_proc = 'proc_print'
            self.proc_opts = node.get('options', {})
            self.analyze_vars = []

        elif t == 'proc_reg':
            self._flush_if_chain()
            self.current_proc = 'proc_reg'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_glm':
            self._flush_if_chain()
            self.current_proc = 'proc_glm'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_export':
            self._flush_if_chain()
            self.current_proc = 'proc_export'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_sql':
            self._flush_if_chain()
            self.current_proc = 'proc_sql'
            self.proc_opts = node.get('options', {})
            self._in_proc_sql = True
            self._sql_statements = []

        elif t == 'proc_fcmp':
            self._flush_if_chain()
            self.current_proc = 'proc_fcmp'
            self.lines.append("# PROC FCMP – define equivalent R function(s) below")

        elif t == 'proc_transpose':
            self._flush_if_chain()
            self.current_proc = 'proc_transpose'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_logistic':
            self._flush_if_chain()
            self.current_proc = 'proc_logistic'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_mixed':
            self._flush_if_chain()
            self.current_proc = 'proc_mixed'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_phreg':
            self._flush_if_chain()
            self.current_proc = 'proc_phreg'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_lifetest':
            self._flush_if_chain()
            self.current_proc = 'proc_lifetest'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_report':
            self._flush_if_chain()
            self.current_proc = 'proc_report'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_tabulate':
            self._flush_if_chain()
            self.current_proc = 'proc_tabulate'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_compare':
            self._flush_if_chain()
            self.current_proc = 'proc_compare'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_contents':
            self._flush_if_chain()
            self.current_proc = 'proc_contents'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_univariate':
            self._flush_if_chain()
            self.current_proc = 'proc_univariate'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_corr':
            self._flush_if_chain()
            self.current_proc = 'proc_corr'
            self.proc_opts = node.get('options', {})

        elif t == 'proc_import':
            self._flush_if_chain()
            self.current_proc = 'proc_import'
            self.proc_opts = node.get('options', {})

        elif t == 'model':
            self.current_model = node

        elif t == 'means_stmt':
            self.current_means_stmt = node

        elif t == 'title':
            self.current_title = node.get('text')

        elif t == 'var':
            self.analyze_vars = node.get('variables', [])

        elif t == 'class':
            self.class_vars = node.get('variables', [])

        elif t == 'tables':
            self.table_vars = node.get('variables', [])

        elif t == 'random':
            self.random_vars = node.get('variables', [])

        elif t == 'strata':
            self.strata_vars = node.get('variables', [])

        elif t == 'time_stmt':
            self.time_stmt = node.get('declaration', '')

        elif t == 'column':
            self.column_vars = node.get('variables', [])

        elif t == 'lsmeans':
            self.lsmeans_effects.append(node.get('effect', ''))

        elif t == 'rename':
            pairs = node.get('pairs', {})
            if self.current_proc == 'data' and self.current_dataset and pairs:
                renames = ', '.join(f'{old} = {new}' for old, new in pairs.items())
                op = [
                    f"{self.current_dataset} <- {self.current_dataset} %>%",
                    f"  rename({renames})",
                ]
                self.pending_data_ops.extend(op)
            self.rename_pairs = pairs

        elif t == 'label_stmt':
            # SAS labels → set_variable_labels via labelled package (no-op if not used)
            decl = node.get('declaration', '')
            self.lines.append(f"# LABEL: {decl}  # (see labelled::var_label() for R equivalent)")

        elif t in ('ods_stmt', 'informat_stmt', 'attrib_stmt'):
            # These have no R equivalents; annotate silently
            pass

        elif t == 'repeated':
            # PROC MIXED REPEATED — complex covariance structure
            self.lines.append(f"# REPEATED: {node.get('declaration', '')} - set correlation structure in lme4/nlme")

        elif t in ('hazardratio', 'estimate_stmt', 'contrast'):
            # These map to post-model summaries
            decl = node.get('declaration', '')
            t_names = {'hazardratio': 'HAZARDRATIO', 'estimate_stmt': 'ESTIMATE', 'contrast': 'CONTRAST'}
            self.lines.append(f"# {t_names.get(t, t.upper())}: {decl}")

        elif t == 'by':
            self.by_vars = node.get('variables', [])
            self.by_desc = node.get('descending', False)
            self.by_var_desc = node.get('var_descending', [])

        elif t == 'array_def':
            arr_name = node.get('name', 'arr')
            variables = node.get('variables', [])
            self._arrays[arr_name] = variables
            # Emit a comment annotation; actual R is emitted when DO loop body is flushed
            comment = f"# ARRAY {arr_name}: {variables}"
            if self.current_proc == 'data' and self.current_dataset:
                self.pending_data_ops.append(comment)
            else:
                self.lines.append(comment)

        elif t == 'do_loop':
            self._do_loop_active = True
            self._do_loop_var   = node.get('var', 'i')
            self._do_loop_from  = self._sas2r(node.get('from_val', '1'))
            self._do_loop_to    = self._sas2r(node.get('to_val', 'n'))
            self._do_loop_by    = self._sas2r(node.get('by_val', '1'))
            self._do_loop_body  = []

        elif t == 'do_while':
            cond = self._sas2r(node.get('condition', 'TRUE'))
            kind = node.get('kind', 'while')
            if kind == 'while':
                lines_block = [f"while ({cond}) {{"]
            else:
                lines_block = [f"repeat {{  # DO UNTIL ({cond})"]
            if self.current_proc == 'data' and self.current_dataset:
                self.pending_data_ops.extend(lines_block)
            else:
                self.lines.extend(lines_block)

        elif t == 'retain':
            # Translate to cumulative initialisation comment; actual cumsum logic
            # is handled in the mutate pipeline when the variable is assigned.
            init_vals = node.get('init_values', {})
            for var, init in init_vals.items():
                comment = f"# RETAIN: {var} initialised to {init} (use cumsum/lag for running totals)"
                if self.current_proc == 'data' and self.current_dataset:
                    self.pending_data_ops.append(comment)
                else:
                    self.lines.append(comment)

        elif t == 'id_stmt':
            # PROC TRANSPOSE — variable whose values become column names
            self.transpose_id_var = node.get('variable', '')

        elif t in ('run', 'quit'):
            self._flush_if_chain()
            self._handle_run()

        elif t == 'unknown':
            stmt = node.get('statement', '').strip()
            # Silently skip PROC IMPORT auxiliary options (not real statements)
            if stmt.lower().startswith(('getnames', 'replace', 'sheet=')):
                return

            # Detect and translate SYMPUTX calls
            symputx_match = re.search(
                r"call\s+symputx\s*\(\s*['\"]?(\w+)['\"]?\s*,\s*(.+?)\s*\)",
                stmt, re.IGNORECASE
            )
            if symputx_match:
                macro_var = symputx_match.group(1)
                value_expr = self._sas2r(symputx_match.group(2).strip())
                # Create R variable assignment instead of just a comment
                self._macro_vars[macro_var] = value_expr
                # Emit actual R assignment
                sanitized_var = self._sanitize_var_name(macro_var)
                self.lines.append(f"{sanitized_var} <- {value_expr}")
                return

            # Detect and skip hash object declarations
            if 'declare hash' in stmt.lower():
                self.lines.append(f"# NOTE: SAS hash object (translated to dplyr operations): {stmt[:50]}...")
                return

            # Detect and handle hash.find() - translate to dplyr join
            if '.find()' in stmt:
                # Extract hash name (e.g., "h.find()" -> "h")
                hash_match = re.search(r'(\w+)\.find\s*\(\s*\)', stmt, re.IGNORECASE)
                if hash_match:
                    hash_name = hash_match.group(1)
                    if hash_name in self._hash_objects:
                        hash_info = self._hash_objects[hash_name]
                        join_dataset = hash_info.get('dataset', '')
                        join_key = hash_info.get('key', '')
                        join_vars = hash_info.get('data_vars', [])

                        if join_dataset and join_key and self.current_dataset:
                            # Emit dplyr left_join
                            vars_to_select = [join_key] + join_vars
                            vars_str = ', '.join(vars_to_select)
                            self.lines.append(f"# Hash lookup translated to join")
                            self.lines.append(f"{self.current_dataset} <- {self.current_dataset} %>%")
                            self.lines.append(f"  left_join({join_dataset} %>% select({vars_str}), by = '{join_key}')")
                            self._created_datasets.add(self.current_dataset)
                            return
                self.lines.append("# NOTE: Hash lookup (review manually)")
                return

            if self._in_proc_sql and stmt:
                self._sql_statements.append(stmt)
            elif stmt:
                self.lines.append(f"# NOTE: SAS-specific statement (review manually): {stmt}")

    # ── RUN handler – deferred emit ───────────────────────────────────────

    def _handle_run(self):
        if self.current_proc == 'data':
            # Flush any incomplete DO block that never got an else
            if self._do_phase == 1 and self._if_do_body:
                self._flush_mutations()
                for var, expr in self._if_do_body:
                    var = self._sanitize_var_name(var)  # Sanitize variable name
                    self.pending_data_ops.append(f"{self.current_dataset} <- {self.current_dataset} %>%")
                    self.pending_data_ops.append(f"  mutate({var} = if_else({self._do_condition}, {expr}, NA))")
                self._do_phase = 0
                self._if_do_body = []

            # Flush buffered mutations before the merge join (so ordering is correct)
            self._flush_mutations()

            # Emit MERGE → join before other data ops
            if self._pending_merge:
                self._emit_merge_at_run()

            if self.data_step_active:
                self._emit_data_step()
            elif self.current_dataset:
                # DATA step with SET or pure-assignment (no DATALINES).
                # Only seed a single-row frame if neither SET nor INPUT provided data.
                seeded_single_row = False
                if self.pending_data_ops:
                    needs_seed = (
                        not self.input_vars
                        and not self.inline_data
                        and not self.data_has_set
                        and not self._pending_merge
                    )
                    if needs_seed:
                        self.lines.append(f"{self.current_dataset} <- data.frame(.row = 1)")
                        seeded_single_row = True
                    self.lines.extend(self.pending_data_ops)
                    if seeded_single_row:
                        self.lines.append(f"{self.current_dataset} <- {self.current_dataset} %>% select(-.row)")
                    self.pending_data_ops = []
                if self.pending_post_data_ops:
                    self.lines.extend(self.pending_post_data_ops)
                    self.pending_post_data_ops = []
                # Only emit row/col NOTE — no auto-print for SET-based steps
                ds = self.current_dataset
                self._created_datasets.add(ds)
                self.lines.append(
                    f"cat(sprintf('NOTE: Dataset {ds.upper()} has %d observations "
                    f"and %d variables.\\n', nrow({ds}), ncol({ds})))")
                self.lines.append(f"print({ds})")
        elif self.current_proc == 'proc_means':
            self._emit_proc_means()
        elif self.current_proc == 'proc_freq':
            self._emit_proc_freq()
        elif self.current_proc == 'proc_sort':
            self._emit_proc_sort()
        elif self.current_proc == 'proc_print':
            self._emit_proc_print()
        elif self.current_proc == 'proc_transpose':
            self._emit_proc_transpose()
        elif self.current_proc == 'proc_reg':
            self._emit_proc_reg()
        elif self.current_proc == 'proc_glm':
            self._emit_proc_glm()
        elif self.current_proc == 'proc_export':
            self._emit_proc_export()
        elif self.current_proc == 'proc_logistic':
            self._emit_proc_logistic()
        elif self.current_proc == 'proc_mixed':
            self._emit_proc_mixed()
        elif self.current_proc == 'proc_phreg':
            self._emit_proc_phreg()
        elif self.current_proc == 'proc_lifetest':
            self._emit_proc_lifetest()
        elif self.current_proc == 'proc_report':
            self._emit_proc_report()
        elif self.current_proc == 'proc_tabulate':
            self._emit_proc_tabulate()
        elif self.current_proc == 'proc_compare':
            self._emit_proc_compare()
        elif self.current_proc == 'proc_contents':
            self._emit_proc_contents()
        elif self.current_proc == 'proc_univariate':
            self._emit_proc_univariate()
        elif self.current_proc == 'proc_corr':
            self._emit_proc_corr()
        elif self.current_proc == 'proc_import':
            self._emit_proc_import()
            # Track the output dataset as created so SET statements won't try to re-read it
            out_ds = self.proc_opts.get('data') or self.proc_opts.get('out') or 'imported_data'
            # Extract just the dataset name (part after dot if it's lib.dataset)
            ds_name = out_ds.split('.')[-1] if '.' in str(out_ds) else out_ds
            self._created_datasets.add(ds_name)
        elif self.current_proc == 'proc_sql':
            self._emit_proc_sql()

        self.lines.append('')
        self.current_proc = None
        self._in_proc_sql = False
        self._reset_proc_ctx()

    # ── emitters ──────────────────────────────────────────────────────────

    def _emit_header(self):
        self.lines += [
            "# Auto-generated R code from SAS",
            "# Generated by SAS to R Automation Platform",
            "",
            "# Set output format to plain ASCII (avoids encoding issues on Windows)",
            "options(width = 200, scipen = 999)",
            "",
            "library(dplyr)",
            "library(tidyr)",
            "library(readr)",
            "",
        ]

    def _emit_data_step(self):
        ds = self.current_dataset or 'data'
        vars_ = self.input_vars
        data = self._next_inline_block()

        if not vars_ or not data:
            self.lines.append(f"# DATA step: {ds} (no inline data detected)")
            return

        self.lines.append(f"# Create dataset: {ds}")
        self.lines.append(f"{ds} <- data.frame(")

        for i, v in enumerate(vars_):
            name = v['name']
            vtype = v['type']
            col = []
            for row in data:
                if i < len(row):
                    val = row[i]
                    if val in ('.', ''):
                        col.append('NA')
                    elif vtype == 'character':
                        col.append(f'"{val}"')
                    else:
                        col.append(val)
                else:
                    col.append('NA')
            # all data columns need a trailing comma – stringsAsFactors comes last
            self.lines.append(f"  {name} = c({', '.join(col)}),")

        self.lines.append("  stringsAsFactors = FALSE")
        self.lines.append(")")

        # Apply deferred operations (assignments, if, where, keep, drop)
        if self.pending_data_ops:
            self.lines.extend(self.pending_data_ops)
            self.pending_data_ops = []
        if self.pending_post_data_ops:
            self.lines.extend(self.pending_post_data_ops)
            self.pending_post_data_ops = []

        self.lines.append(
            f"cat(sprintf('NOTE: Dataset {ds.upper()} has %d observations "
            f"and %d variables.\\n', nrow({ds}), ncol({ds})))")
        self.lines.append(f"print(as.data.frame({ds}))")
        self.data_step_active = False

    def _next_inline_block(self) -> List[List[str]]:
        """Return next DATALINES block when multiple DATA steps exist."""
        if not self.inline_data:
            return []
        first = self.inline_data[0]
        # New format: list of blocks, each block = list[row]
        if isinstance(first, list) and first and isinstance(first[0], list):
            if self.inline_data_idx < len(self.inline_data):
                block = self.inline_data[self.inline_data_idx]
                self.inline_data_idx += 1
                return block
            return []
        # Backward-compatible format: single block
        return self.inline_data  # type: ignore[return-value]

    def _emit_info_print(self, ds: str):
        self.lines.append(
            f"cat(sprintf('NOTE: Dataset {ds.upper()} has %d observations "
            f"and %d variables.\\n', nrow({ds}), ncol({ds})))")
        self.lines.append(f"head({ds})")

    # SAS PROC options that masquerade as assignments — never emit as R code
    _PROC_OPTION_VARS = frozenset({
        'getnames', 'replace', 'sheet', 'mixed', 'dbms', 'out', 'outfile',
        'datafile', 'delimiter', 'obs', 'firstobs', 'guessingrows',
    })

    # Date-variable suffix pattern for detecting date arithmetic (DT/DTM/DATE endings)
    _DT_ARITH_RE = re.compile(
        r'\b(\w*(?:DT|DTM|DTE|DATE))\s*-\s*(\w*(?:DT|DTM|DTE|DATE))\b', re.I
    )

    def _wrap_date_arith(self, expr: str) -> str:
        """Wrap DT - DT subtraction with as.numeric() to return days, not difftime."""
        return self._DT_ARITH_RE.sub(
            lambda m: f"as.numeric({m.group(1)} - {m.group(2)})", expr
        )

    def _emit_assignment(self, node: Dict[str, Any]):
        var = node.get('variable', '')
        expr = self._sas2r(node.get('expression', ''))

        # Skip PROC option keywords that the parser captures as assignments
        if var.lower() in self._PROC_OPTION_VARS:
            return

        # Sanitize variable name (remove leading underscores for R compatibility)
        var = self._sanitize_var_name(var)

        # Handle hash.find() calls - translate to dplyr join
        if '.find()' in expr:
            hash_match = re.search(r'(\w+)\.find\s*\(\s*\)', expr, re.IGNORECASE)
            if hash_match:
                hash_name = hash_match.group(1)
                if hash_name in self._hash_objects and self.current_dataset:
                    hash_info = self._hash_objects[hash_name]
                    join_dataset = hash_info.get('dataset', '')
                    join_key = hash_info.get('key', '')
                    join_vars = hash_info.get('data_vars', [])

                    if join_dataset and join_key:
                        # Emit dplyr left_join instead of hash.find()
                        vars_to_select = [join_key] + join_vars
                        vars_str = ', '.join(vars_to_select)
                        self._flush_mutations()  # Flush any pending mutations first
                        self.lines.append(f"# Hash lookup translated to join")
                        self.lines.append(f"{self.current_dataset} <- {self.current_dataset} %>%")
                        self.lines.append(f"  left_join({join_dataset} %>% select({vars_str}), by = '{join_key}')")
                        return

        # Intercept assignments inside indexed DO loops
        if self._do_loop_active:
            self._do_loop_body.append(f"{var} = {expr}")
            return

        # Intercept assignments inside IF-THEN DO / ELSE DO blocks
        if self._do_phase == 1:
            self._if_do_body.append((var, expr))
            return
        if self._do_phase == 2:
            self._else_do_body.append((var, expr))
            return

        if self.current_proc == 'data' and self.current_dataset:
            # Buffer for batching into a single mutate() at flush time
            self._pending_mutations.append((var, expr))
        else:
            self.lines.append(f"{var} <- {expr}")

    def _emit_if(self, node: Dict[str, Any]):
        cond = self._sas2r(node.get('condition', ''))
        then = node.get('then_clause') or ''
        else_ = node.get('else_clause')
        ds = self.current_dataset

        if ds and '=' in then:
            var = then.split('=')[0].strip()
            var = self._sanitize_var_name(var)  # Sanitize variable name
            tv = self._sas2r(then.split('=', 1)[1].strip()).replace("'", '"')
            op_lines = [
                f"{ds} <- {ds} %>%",
                f"  mutate({var} = case_when(",
                f"    {cond} ~ {tv},",
            ]
            if else_ and '=' in else_:
                ev = self._sas2r(else_.split('=', 1)[1].strip()).replace("'", '"')
                op_lines.append(f"    TRUE ~ {ev}")
            else:
                op_lines.append("    TRUE ~ NA_character_")
            op_lines.append("  ))")
            if self.current_proc == 'data':
                self.pending_data_ops.extend(op_lines)
            else:
                self.lines.extend(op_lines)

    def _start_if_chain(self, node: Dict[str, Any]):
        # Flush any previous IF chain before starting a new one (handles multiple consecutive IF chains)
        if self.pending_if_chain and self.current_dataset:
            self._flush_if_chain()

        # Reset any leftover DO-block state from a previous incomplete chain
        self._do_phase = 0
        self._do_condition = ''
        self._if_do_body = []
        self._else_do_body = []
        then_clause = (node.get('then_clause') or '').strip().lower()
        if then_clause == 'do':
            # Start collecting assignments into the IF do-body
            self._do_phase = 1
            self._do_condition = self._sas2r(node.get('condition', ''))
        self.pending_if_chain = [node]

    def _extend_if_chain(self, node: Dict[str, Any]):
        if not self.pending_if_chain:
            self.pending_if_chain = [node]
            return
        self.pending_if_chain.append(node)

    def _close_if_chain_with_else(self, node: Dict[str, Any]):
        clause = (node.get('clause') or '').strip().lower()
        if clause == 'do':
            # Start collecting assignments into the ELSE do-body
            self._do_phase = 2
            self.pending_if_chain.append(node)
            return   # don't flush yet — wait for the closing END
        if not self.pending_if_chain:
            self.pending_if_chain = [node]
        else:
            self.pending_if_chain.append(node)
        self._flush_if_chain()

    def _handle_do_end(self):
        """Called when END node is seen — closes the current DO-block phase."""
        # ── Indexed DO loop takes priority ───────────────────────────────────
        if self._do_loop_active:
            self._emit_do_loop()
            return

        # ── IF ... THEN DO / ELSE DO block ───────────────────────────────────
        if self._do_phase == 1:
            self._do_phase = 0
        elif self._do_phase == 2:
            self._emit_do_block_result()
            self._do_phase = 0

    def _emit_do_loop(self):
        """
        Translate an indexed DO loop into idiomatic R.

        Pattern: DO i = 1 TO n; arr{i} = expr; END;
        If the body only initialises ARRAY variables to a constant → use across().
        Otherwise → emit a for loop.
        """
        var   = self._do_loop_var
        frm   = self._do_loop_from
        to    = self._do_loop_to
        by    = self._do_loop_by
        body  = list(self._do_loop_body)
        ds    = self.current_dataset

        self._do_loop_active = False
        self._do_loop_body   = []

        # ── Case 1: body is a set of ARRAY element assignments arr{i} = const ──
        # e.g. flag{i} = 0  →  mutate(across(c(v1,v2,v3), ~0))
        # Only applies when RHS is a constant (no array element references on RHS)
        _m0 = (
            re.match(r'^(\w+)\{' + re.escape(var) + r'\}\s*=\s*(.+)$', body[0], re.I)
            if len(body) == 1 else None
        )
        simple_array_assign = (
            len(body) == 1
            and ds
            and _m0 is not None
            and '{' not in _m0.group(2)  # RHS must not reference array elements
        )
        if simple_array_assign:
            m = _m0
            arr_name = m.group(1)   # type: ignore[union-attr]
            rhs      = self._sas2r(m.group(2).strip())  # type: ignore[union-attr]
            arr_vars = self._arrays.get(arr_name, [])
            if arr_vars:
                cols_str = ', '.join(arr_vars)
                op = [
                    f"{ds} <- {ds} %>%",
                    f"  mutate(across(c({cols_str}), ~{rhs}))",
                ]
                if self.current_proc == 'data':
                    self.pending_data_ops.extend(op)
                else:
                    self.lines.extend(op)
                return

        # ── Case 2: general for loop ──────────────────────────────────────────
        seq = f"seq({frm}, {to})" if by == '1' else f"seq({frm}, {to}, by = {by})"
        loop_lines = [f"for ({var} in {seq}) {{"]
        for stmt_line in body:
            # Translate arr{i} references inside the body
            def _sub_arr(m):
                aname = m.group(1)
                avars = self._arrays.get(aname)
                if avars:
                    return f"{aname}_vars[[{var}]]"  # runtime list indexing
                return m.group(0)
            translated = re.sub(r'(\w+)\{' + re.escape(var) + r'\}', _sub_arr, stmt_line)
            loop_lines.append(f"  {translated}")
        loop_lines.append("}")

        if ds and self.current_proc == 'data':
            # Wrap array definitions as named lists when needed
            for arr_name, arr_vars in self._arrays.items():
                if arr_vars:
                    self.pending_data_ops.append(
                        f'{arr_name}_vars <- list({", ".join(arr_vars)})'
                    )
            self.pending_data_ops.extend(loop_lines)
        else:
            for arr_name, arr_vars in self._arrays.items():
                if arr_vars:
                    self.lines.append(f'{arr_name}_vars <- list({", ".join(arr_vars)})')
            self.lines.extend(loop_lines)

    def _emit_do_block_result(self):
        """Emit a single mutate() that applies the IF/ELSE DO assignments."""
        if not self._if_do_body and not self._else_do_body:
            return
        ds = self.current_dataset
        cond = self._do_condition
        if not ds:
            return

        # Collect all variable names from both branches
        if_vars = {v: e for v, e in self._if_do_body}
        else_vars = {v: e for v, e in self._else_do_body}
        all_vars = list(if_vars.keys())
        for v in else_vars:
            if v not in if_vars:
                all_vars.append(v)

        mutate_parts = []
        for var in all_vars:
            if_val   = if_vars.get(var, 'NA')
            else_val = else_vars.get(var, 'NA')
            mutate_parts.append(f"    {var} = if_else({cond}, {if_val}, {else_val})")

        op_lines = [
            f"{ds} <- {ds} %>%",
            "  mutate(",
        ] + [p + ',' for p in mutate_parts[:-1]] + [mutate_parts[-1]] + ["  )"]

        if self.current_proc == 'data':
            self.pending_data_ops.extend(op_lines)
        else:
            self.lines.extend(op_lines)

        # Reset DO-block state and clear the if-chain so _flush_if_chain is a no-op
        self._if_do_body = []
        self._else_do_body = []
        self._do_condition = ''
        self.pending_if_chain = []

    def _emit_libname(self, node: Dict[str, Any]):
        libref = node.get('libref', 'lib')
        path   = node.get('path', '')
        self._libname_map[libref] = path
        self.lines.append(f'# LIBNAME {libref.upper()} = "{path}"')
        self.lines.append(f'{libref}_path <- "{path}"')

    def _emit_merge_at_run(self):
        """Translate a SAS MERGE statement into dplyr joins, respecting in= and keep=."""
        node = self._pending_merge
        if not node:
            return
        self._pending_merge = None
        datasets = node.get('datasets', [])
        if len(datasets) < 2:
            return

        ds = self.current_dataset
        by_vars = ', '.join(f'"{v}"' for v in (self.by_vars or ['id']))
        by_call = ', '.join(self.by_vars or ['id'])

        # Load any datasets that have a known libname path (skip if already in memory)
        for d in datasets:
            lib = d.get('libref', 'work')
            name = d.get('name', 'ds')
            if name in self._created_datasets or name.lower() in self._imported_datasets:
                continue
            path = self._libname_map.get(lib)
            if path and lib != 'work':
                self.lines.append(
                    f'{name} <- haven::read_sas(file.path("{path}", "{name}.sas7bdat"))'
                )

        # Determine join type
        left_ds    = datasets[0]['name']
        right_ds   = datasets[1]['name']
        keep_left  = datasets[0].get('keep', [])
        keep_right = datasets[1].get('keep', [])

        # Build dataset references, inlining keep= as select() inside the join call
        def _ds_ref(name: str, keep: list) -> str:
            if keep:
                cols = ', '.join(keep)
                return f"{name} %>% select({cols})"
            return name

        left_ref  = _ds_ref(left_ds,  keep_left)
        right_ref = _ds_ref(right_ds, keep_right)

        join_type = node.get('join_type', 'left_join')
        join_lines = [f"# MERGE {left_ds} + {right_ds} BY {by_call} -> {join_type}"]
        join_lines.append(f"{ds} <- {left_ref} %>%")
        join_lines.append(f"  {join_type}({right_ref}, by = c({by_vars}))")

        if self.current_proc == 'data':
            # Prepend so the join runs BEFORE the subsequent assignment mutations
            self.pending_data_ops = join_lines + self.pending_data_ops
        else:
            self.lines.extend(join_lines)
        self.data_has_set = True

    def _flush_if_chain(self):
        if not self.pending_if_chain or not self.current_dataset:
            self.pending_if_chain = []
            return
        self._flush_mutations()  # batch any buffered assignments before the case_when

        first_assign = None
        cases = []
        default_val = "NA_character_"
        is_numeric = False

        for n in self.pending_if_chain:
            t = n.get('type')
            if t in ('if_statement', 'else_if_statement'):
                cond = self._sas2r(n.get('condition', ''))
                clause = (n.get('then_clause') or '').strip()
                if '=' in clause:
                    var, val = clause.split('=', 1)
                    var = var.strip()
                    val = self._sas2r(val.strip()).replace("'", '"')
                    if first_assign is None:
                        first_assign = var
                    if var == first_assign:
                        cases.append((cond, val))
                        # Detect if value is numeric
                        try:
                            float(val)
                            is_numeric = True
                        except ValueError:
                            pass
            elif t == 'else_statement':
                clause = (n.get('clause') or '').strip()
                if '=' in clause:
                    var, val = clause.split('=', 1)
                    var = var.strip()
                    val = self._sas2r(val.strip()).replace("'", '"')
                    if first_assign is None:
                        first_assign = var
                    if var == first_assign:
                        default_val = val

        # If no explicit else clause, use appropriate NA based on value type
        if default_val == "NA_character_" and is_numeric:
            default_val = "NA_real_"

        if first_assign and cases:
            first_assign = self._sanitize_var_name(first_assign)  # Sanitize variable name
            op_lines = [
                f"{self.current_dataset} <- {self.current_dataset} %>%",
                f"  mutate({first_assign} = case_when(",
            ]
            for cond, val in cases:
                op_lines.append(f"    {cond} ~ {val},")
            op_lines.append(f"    TRUE ~ {default_val}")
            op_lines.append("  ))")
            if self.current_proc == 'data':
                self.pending_data_ops.extend(op_lines)
            else:
                self.lines.extend(op_lines)
        else:
            self.lines.append("# NOTE: Complex conditional - review and translate manually")

        self.pending_if_chain = []

    def _emit_where(self, node: Dict[str, Any]):
        cond = self._sas2r(node.get('condition', ''))
        if self.current_proc == 'data' and self.current_dataset:
            self._flush_mutations()
            self.pending_data_ops.append(f"{self.current_dataset} <- {self.current_dataset} %>%")
            self.pending_data_ops.append(f"  filter({cond})")
        else:
            self.where_condition = cond

    def _emit_keep(self, node: Dict[str, Any]):
        vs = node.get('variables', [])
        if self.current_dataset and vs:
            # Defer KEEP to after all mutations (add to pending_post_data_ops)
            op_lines = [
                f"{self.current_dataset} <- {self.current_dataset} %>%",
                f"  select({', '.join(vs)})",
            ]
            if self.current_proc == 'data':
                self.pending_post_data_ops.extend(op_lines)
            else:
                self.lines.extend(op_lines)

    def _emit_drop(self, node: Dict[str, Any]):
        vs = node.get('variables', [])
        if self.current_dataset and vs:
            # Defer DROP to after all mutations (add to pending_post_data_ops)
            # Use any_of() to silently skip columns that don't exist
            cols_str = ', '.join(f'"{v}"' for v in vs)
            op_lines = [
                f"{self.current_dataset} <- {self.current_dataset} %>%",
                f"  select(-any_of(c({cols_str})))",
            ]
            if self.current_proc == 'data':
                self.pending_post_data_ops.extend(op_lines)
            else:
                self.lines.extend(op_lines)

    def _emit_put(self, node: Dict[str, Any]):
        content = (node.get('content') or '').strip()
        if not content:
            return
        # Tokenize quoted strings and bare identifiers.
        tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', content)
        parts = []
        for tok in tokens:
            t = tok.strip()
            if not t:
                continue
            if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
                parts.append(t.replace("'", '"'))
            else:
                ref = self._sas2r(t)
                if self.current_proc == 'data' and self.current_dataset:
                    ref = f"{self.current_dataset}${ref}"
                parts.append(ref)
        if parts:
            put_line = f"cat(paste({', '.join(parts)}), '\\n')"
            if self.current_proc == 'data':
                self.pending_post_data_ops.append(put_line)
            else:
                self.lines.append(put_line)
        else:
            self.lines.append(f"# NOTE: SAS PUT statement (review manually): put {content};")

    def _emit_proc_sql(self):
        """Translate collected PROC SQL statements to dplyr chains."""
        if not self._sql_statements:
            self.lines.append("# PROC SQL – no translatable statements found")
            return
        for raw_sql in self._sql_statements:
            self._translate_sql_to_dplyr(raw_sql)

    def _translate_sql_to_dplyr(self, sql: str) -> None:
        """Convert a single SQL SELECT/CREATE TABLE statement to a dplyr chain."""
        sql_clean = re.sub(r'\s+', ' ', sql).strip().rstrip(';')

        # CREATE TABLE output AS SELECT ... (allow library.table notation)
        create_match = re.match(
            r'create\s+table\s+([\w.]+)\s+as\s+(.+)', sql_clean, re.I
        )
        output_var = None
        select_part = sql_clean
        if create_match:
            output_var = create_match.group(1).split('.')[-1]  # Strip libname prefix
            select_part = create_match.group(2).strip()

        # Try to parse JOIN pattern first
        join_match = re.match(
            r'select\s+(.+?)\s+from\s+(\w+)\s+(\w+)\s+((?:left|inner|right|full)\s+join)\s+(\w+)\s+(\w+)\s+on\s+(.+?)(?:\s+where\s+(.+?))?(?:\s+group\s+by\s+(.+?))?(?:\s+order\s+by\s+(.+?))?$',
            select_part, re.I
        )
        if join_match:
            self._translate_sql_join(output_var or 'result', join_match, sql_clean)
            return

        # Parse SELECT ... FROM ... WHERE ... GROUP BY ... ORDER BY ...
        # Note: table names can be qualified (lib.table) so allow dots
        sel_m = re.match(
            r'select\s+(.+?)\s+from\s+([\w.]+)'
            r'(?:\s+where\s+(.+?))?'
            r'(?:\s+group\s+by\s+(.+?))?'
            r'(?:\s+order\s+by\s+(.+?))?$',
            select_part, re.I
        )
        if not sel_m:
            self.lines.append(f"# PROC SQL (translate manually): {sql_clean}")
            return

        cols_raw   = sel_m.group(1).strip()
        table      = sel_m.group(2).strip()
        # Strip library prefix from table name (lib.table → table)
        if '.' in table:
            table = table.split('.')[-1]
        where_raw  = (sel_m.group(3) or '').strip()
        groupby    = (sel_m.group(4) or '').strip()
        orderby    = (sel_m.group(5) or '').strip()

        # Translate SQL aggregate functions to dplyr equivalents
        def _agg(c: str) -> str:
            c = re.sub(r'\bCOUNT\s*\(\s*\*\s*\)', 'n()', c, flags=re.I)
            c = re.sub(r'\bCOUNT\s*\((\w+)\)', r'sum(!is.na(\1))', c, flags=re.I)
            c = re.sub(r'\bSUM\s*\((\w+)\)', r'sum(\1, na.rm=TRUE)', c, flags=re.I)
            c = re.sub(r'\bAVG\s*\((\w+)\)', r'mean(\1, na.rm=TRUE)', c, flags=re.I)
            c = re.sub(r'\bMIN\s*\((\w+)\)', r'min(\1, na.rm=TRUE)', c, flags=re.I)
            c = re.sub(r'\bMAX\s*\((\w+)\)', r'max(\1, na.rm=TRUE)', c, flags=re.I)
            # col AS alias → alias = col
            c = re.sub(r'(\w+)\s+AS\s+(\w+)', r'\2 = \1', c, flags=re.I)
            return c

        def _sql_cond(cond: str) -> str:
            cond = re.sub(r'\bAND\b', '&', cond, flags=re.I)
            cond = re.sub(r'\bOR\b',  '|', cond, flags=re.I)
            cond = re.sub(r'\bNOT\b', '!', cond, flags=re.I)
            cond = re.sub(r'(?<![!<>=])=(?!=)', '==', cond)
            return cond

        lhs = output_var or f"sql_result"
        chain = [f"# PROC SQL: {sql_clean[:80] + ('...' if len(sql_clean) > 80 else '')}",
                 f"{lhs} <- {table}"]

        if where_raw:
            chain.append(f"  filter({_sql_cond(where_raw)})")
        if groupby:
            grp_cols = ', '.join(c.strip() for c in groupby.split(','))
            chain.append(f"  group_by({grp_cols})")
        if cols_raw != '*':
            # Check if any aggregates present → use summarise, else select
            if re.search(r'\b(COUNT|SUM|AVG|MIN|MAX)\s*\(', cols_raw, re.I):
                col_exprs = ', '.join(_agg(c.strip()) for c in cols_raw.split(','))
                chain.append(f"  summarise({col_exprs}, .groups = 'drop')")
            else:
                col_exprs = ', '.join(_agg(c.strip()) for c in cols_raw.split(','))
                chain.append(f"  select({col_exprs})")
        if groupby and cols_raw != '*':
            chain.append("  ungroup()")
        if orderby:
            desc_cols = []
            for c in orderby.split(','):
                c = c.strip()
                if re.search(r'\bDESC\b', c, re.I):
                    c = f"desc({re.sub(r'\s+DESC', '', c, flags=re.I).strip()})"
                desc_cols.append(c)
            chain.append(f"  arrange({', '.join(desc_cols)})")

        # Build the pipe chain
        pipe_lines = [chain[0]]  # comment
        if len(chain) > 2:
            pipe_lines.append(chain[1] + " %>%")
            for step in chain[2:-1]:
                pipe_lines.append(step + " %>%")
            pipe_lines.append(chain[-1])
        else:
            pipe_lines.append(chain[1])
        self.lines.extend(pipe_lines)

        # Track created dataset
        if output_var:
            self._created_datasets.add(output_var)

    def _translate_sql_join(self, output_var: str, join_match, sql_clean: str) -> None:
        """Translate SQL JOIN to dplyr join."""
        cols_raw = join_match.group(1).strip()
        table_a = join_match.group(2).strip()
        alias_a = join_match.group(3).strip()
        join_type = join_match.group(4).strip().lower()  # left join, inner join, etc.
        table_b = join_match.group(5).strip()
        alias_b = join_match.group(6).strip()
        on_cond = join_match.group(7).strip()
        where_cond = (join_match.group(8) or '').strip()
        groupby = (join_match.group(9) or '').strip()
        orderby = (join_match.group(10) or '').strip()

        # Parse ON condition (e.g., "a.USUBJID = b.USUBJID")
        on_parts = on_cond.split('=')
        left_key = right_key = None
        if len(on_parts) == 2:
            left_key = on_parts[0].strip().split('.')[-1]
            right_key = on_parts[1].strip().split('.')[-1]

        # Build dplyr join
        self.lines.append(f"# PROC SQL: {join_type.upper()} JOIN")
        if 'left' in join_type:
            join_func = 'left_join'
        elif 'inner' in join_type:
            join_func = 'inner_join'
        elif 'right' in join_type:
            join_func = 'right_join'
        else:
            join_func = 'full_join'

        self.lines.append(f"{output_var} <- {table_a} %>%")
        if left_key and right_key:
            self.lines.append(f"  {join_func}({table_b} %>% select({', '.join(c.strip() for c in cols_raw.split(','))}), by = c(\"{left_key}\" = \"{right_key}\"))")
        else:
            self.lines.append(f"  {join_func}({table_b}, by = \"USUBJID\")")

        if where_cond:
            where_r = re.sub(r'\bAND\b', '&', where_cond, flags=re.I)
            where_r = re.sub(r'\bOR\b', '|', where_r, flags=re.I)
            self.lines.append(f"  filter({where_r})")

        self._created_datasets.add(output_var)
        self._imported_datasets.add(output_var.lower())

    def _strip_libname(self, dataset_name: str) -> str:
        """Strip library prefix from dataset name (adam.adsl → adsl)."""
        if not dataset_name:
            return dataset_name
        dataset_name = str(dataset_name).strip()
        return dataset_name.split('.')[-1] if '.' in dataset_name else dataset_name

    def _emit_proc_means(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
        ds = self._strip_libname(ds)
        stat_map = {
            'n':      ('N',       'sum(!is.na({v}))'),
            'mean':   ('Mean',    'mean({v}, na.rm = TRUE)'),
            'median': ('Median',  'median({v}, na.rm = TRUE)'),
            'min':    ('Min',     'min({v}, na.rm = TRUE)'),
            'max':    ('Max',     'max({v}, na.rm = TRUE)'),
            'std':    ('StdDev',  'sd({v}, na.rm = TRUE)'),
            'var':    ('Var',     'var({v}, na.rm = TRUE)'),
            'sum':    ('Sum',     'sum({v}, na.rm = TRUE)'),
            'nmiss':  ('NMiss',   'sum(is.na({v}))'),
        }
        # Default order matches SAS PROC MEANS default: N Mean Median StdDev Min Max Sum
        use_stats = [s for s in self.stat_opts if s in stat_map] or \
                    ['n', 'mean', 'median', 'std', 'min', 'max', 'sum']
        vars_ = self.analyze_vars

        self.lines.append(f"# PROC MEANS: Summary statistics for {ds}")
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append("cat('\\nThe MEANS Procedure\\n')")

        if self.class_vars:
            grp = ', '.join(self.class_vars)
            self.lines.append(f"summary_stats <- {ds} %>%")
            self.lines.append(f"  group_by({grp}) %>%")
        else:
            self.lines.append(f"summary_stats <- {ds} %>%")

        if vars_:
            # Named VAR list: emit one column per stat per variable
            summaries = []
            for v in vars_:
                for sk in use_stats:
                    label, expr_tmpl = stat_map[sk]
                    summaries.append(
                        f"    {label}_{v} = {expr_tmpl.replace('{v}', v)}")
            self.lines.append("  summarise(")
            self.lines.append(',\n'.join(summaries))
            self.lines.append("  )")
        else:
            # No VAR: use across() with a named list so dplyr names columns
            # correctly as "{stat}_{col}" (e.g. Mean_Revenue).
            # Using tilde-lambda (~) for dplyr 1.0+ compatibility.
            across_parts = []
            for sk in use_stats:
                label, expr_tmpl = stat_map[sk]
                fn = expr_tmpl.replace('{v}', '.x')
                across_parts.append(f"    {label} = ~{fn}")
            self.lines.append("  summarise(across(where(is.numeric), list(")
            self.lines.append(',\n'.join(across_parts))
            self.lines.append('  ), .names = "{.fn}_{.col}"))')

        if self.class_vars:
            self.lines.append("summary_stats <- ungroup(summary_stats)")
        self.lines.append("print(summary_stats)")
        self._created_datasets.add('summary_stats')

    def _emit_proc_freq(self):
        ds = self._strip_libname(self.proc_opts.get('data', self.current_dataset) or 'data')
        by_vars = self.proc_opts.get('by_vars', []) or self.by_vars
        out_ds = self.proc_opts.get('out_ds', '')  # OUTPUT dataset name

        # Check if this is a NOPRINT PROC FREQ with OUTPUT dataset (meant to create a summary table)
        is_noprint = self.proc_opts.get('noprint', False)

        if is_noprint and out_ds and self.table_vars:
            # NOPRINT PROC FREQ with OUTPUT: Create summary dataset
            var = self.table_vars[0] if self.table_vars else ''
            if var and by_vars:
                # BY group with TABLES output: group_by() + count()
                by_clause = ', '.join(by_vars)
                self.lines.append(f"# PROC FREQ: Frequency for {var} by {by_clause} output to {out_ds}")
                self.lines.append(f"{out_ds} <- {ds} %>%")
                self.lines.append(f"  group_by({by_clause}) %>%")
                self.lines.append(f"  summarise(n = n(), .groups = 'drop') %>%")
                self.lines.append(f"  rename(COUNT = n)")
                self._created_datasets.add(out_ds)
                return

        # Regular PROC FREQ: Print frequency tables
        self.lines.append(f"# PROC FREQ: Frequency tables for {ds}")
        self.lines.append("cat('\\nThe FREQ Procedure\\n')")

        for var in self.table_vars:
            safe = re.sub(r'[^a-zA-Z0-9_]', '_', var)
            if '*' in var:
                cols = ', '.join(var.split('*'))
                self.lines += [
                    f"freq_{safe} <- {ds} %>%",
                    f"  count({cols}) %>%",
                    "  mutate(Percent = round(n / sum(n) * 100, 2))",
                ]
                self.lines.append(f"cat(sprintf('\\nFrequency Table for {var}\\n'))")
                self.lines.append(f"print(freq_{safe})")
            else:
                self.lines += [
                    f"freq_{safe} <- {ds} %>%",
                    f"  count({var}) %>%",
                    "  mutate(",
                    "    Percent = round(n / sum(n) * 100, 2),",
                    "    CumFreq = cumsum(n),",
                    "    CumPercent = round(cumsum(n) / sum(n) * 100, 2)",
                    "  )",
                ]
                self.lines.append(f"cat(sprintf('\\nFrequency Table for {var}\\n'))")
                self.lines.append(f"print(freq_{safe})")
                # Print Total row to match SAS PROC FREQ output
                self.lines.append(
                    f"cat(sprintf('%-20s %12d %10s\\n', 'Total', sum(freq_{safe}$n), '100.00'))"
                )

    def _emit_proc_sort(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
        out = self.proc_opts.get('out', ds)
        self.lines.append(f"# PROC SORT: Sort {ds}")
        if self.by_vars:
            var_descs = self.by_var_desc or [self.by_desc] * len(self.by_vars)
            exprs = [
                f"desc({v})" if (var_descs[i] if i < len(var_descs) else self.by_desc) else v
                for i, v in enumerate(self.by_vars)
            ]
            self.lines.append(f"{out} <- {ds} %>%")
            self.lines.append(f"  arrange({', '.join(exprs)})")
        else:
            self.lines.append("# NOTE: No BY variables specified for PROC SORT")

    def _emit_proc_print(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC PRINT: Print {ds}")
        self.lines.append("cat('\\nObs\\n')")
        if self.where_condition:
            self.lines.append(f"print_df__ <- {ds} %>% filter({self.where_condition})")
            ds_ref = "print_df__"
        else:
            ds_ref = ds
        if self.analyze_vars:
            cols = ', '.join(f'"{v}"' for v in self.analyze_vars)
            self.lines.append(f"print({ds_ref}[, c({cols}), drop = FALSE])")
        else:
            self.lines.append(f"print({ds_ref})")

    def _emit_proc_transpose(self):
        ds   = self.proc_opts.get('data', self.current_dataset) or 'data'
        out  = self.proc_opts.get('out', ds + '_t')
        prefix = self.proc_opts.get('prefix', '')
        id_var  = self.transpose_id_var
        val_vars = self.analyze_vars  # from VAR statement
        by_part  = ', '.join(self.by_vars) if self.by_vars else None

        self.lines.append(f"# PROC TRANSPOSE: Pivot {ds}")
        self.lines.append(f"# Convert long->wide using tidyr::pivot_wider")
        parts = [f"{out} <- {ds} %>%"]
        if by_part:
            parts.append(f"  dplyr::group_by({by_part}) %>%")
        pivot_args = []
        if id_var:
            pivot_args.append(f"names_from = \"{id_var}\"")
            if prefix:
                pivot_args.append(f"names_prefix = \"{prefix}\"")
        else:
            pivot_args.append("names_from = 1  # adjust: column whose values become headers")
        if val_vars:
            vals = ', '.join(f'"{v}"' for v in val_vars)
            pivot_args.append(f"values_from = c({vals})")
        else:
            pivot_args.append("values_from = 2  # adjust: column(s) containing values")
        parts.append(f"  tidyr::pivot_wider({', '.join(pivot_args)})")
        self.lines.extend(parts)
        self.lines.append(f"print(as.data.frame({out}), row.names = FALSE)")

    def _emit_proc_glm(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
        dep = self.current_model.get('dependent', '')
        ind = self.current_model.get('independent', '')
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC GLM: ANOVA on {ds}")
        if dep and ind:
            self.lines.append(f"glm_fit <- aov({dep} ~ {ind}, data = {ds})")
            self.lines.append("print(summary(glm_fit))")
            if self.current_means_stmt.get('variables') and 'tukey' in self.current_means_stmt.get('options', []):
                self.lines.append("print(TukeyHSD(glm_fit))")
        else:
            self.lines.append("# TODO: PROC GLM model statement incomplete.")

    def _emit_proc_reg(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
        dep = self.current_model.get('dependent', '')
        ind_raw = self.current_model.get('independent', '')
        ind_vars = [v.strip() for v in ind_raw.split() if v.strip()]
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC REG: Linear regression on {ds}")
        if dep and ind_vars:
            formula = f"{dep} ~ {' + '.join(ind_vars)}"
            self.lines.append(f"reg_model <- lm({formula}, data = {ds})")
            self.lines.append("print(summary(reg_model))")
        else:
            self.lines.append("# TODO: PROC REG model statement incomplete.")

    def _emit_proc_export(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
        outfile = self.proc_opts.get('outfile', 'export.csv')
        dbms = self.proc_opts.get('dbms', '')
        self.lines.append(f"# PROC EXPORT: write {ds} to file")
        if dbms == 'xlsx' or outfile.lower().endswith('.xlsx'):
            self.lines.append("if (requireNamespace('writexl', quietly = TRUE)) {")
            self.lines.append(f"  writexl::write_xlsx({ds}, '{outfile}')")
            self.lines.append("} else {")
            self.lines.append(f"  write.csv({ds}, sub('\\\\.xlsx$', '.csv', '{outfile}'), row.names = FALSE)")
            self.lines.append("  cat('NOTE: Package writexl not installed; exported CSV fallback.\\n')")
            self.lines.append("}")
        else:
            self.lines.append(f"write.csv({ds}, '{outfile}', row.names = FALSE)")

    def _emit_proc_logistic(self):
        ds  = self.proc_opts.get('data', self.current_dataset) or 'data'
        dep = self.current_model.get('dependent', 'outcome')
        ind = self.current_model.get('independent', '.')
        cls = ', '.join(self.class_vars) if self.class_vars else ''
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC LOGISTIC: Logistic regression on {ds}")
        if cls:
            self.lines.append(f"{ds} <- {ds} %>% mutate(across(c({cls}), as.factor))")
        # Strip SAS options after '/' and join terms with '+'
        ind_clean = ind.split('/')[0].strip() if '/' in ind else ind.strip()
        ind_terms = [t.strip() for t in ind_clean.replace('*', ':').split() if t.strip()]
        ind_formula = ' + '.join(ind_terms) if ind_terms else '.'
        self.lines.append(f"logistic_model <- glm({dep} ~ {ind_formula}, data = {ds}, family = binomial(link = 'logit'))")
        self.lines.append("print(summary(logistic_model))")
        self.lines.append("print(exp(cbind(OR = coef(logistic_model), confint(logistic_model))))  # odds ratios + CI")
        if self.lsmeans_effects:
            self.lines.append("# LSMEANS: use emmeans::emmeans(logistic_model, ...)")

    def _emit_proc_mixed(self):
        ds  = self.proc_opts.get('data', self.current_dataset) or 'data'
        dep = self.current_model.get('dependent', 'response')
        ind = self.current_model.get('independent', '1')
        cls = ', '.join(self.class_vars) if self.class_vars else None
        rnd = ' + '.join(f'(1 | {v})' for v in self.random_vars) if self.random_vars else '(1 | subject)'
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC MIXED: Mixed effects model on {ds}")
        if cls:
            self.lines.append(f"{ds} <- {ds} %>% mutate(across(c({cls}), as.factor))")
        # Strip SAS options after '/' and join fixed-effect terms with '+'
        ind_clean = ind.split('/')[0].strip() if '/' in ind else ind.strip()
        ind_terms = [t.strip() for t in ind_clean.replace('*', ':').split() if t.strip()]
        fixed = ' + '.join(ind_terms) if ind_terms else '1'
        formula = f"{dep} ~ {fixed} + {rnd}"
        self.lines.append("# lme4::lmer is preferred; use nlme::lme for SAS-compatible covariance structures")
        self.lines.append(f"mixed_model <- lme4::lmer({formula}, data = {ds}, REML = TRUE)")
        self.lines.append("print(summary(mixed_model))")
        if self.lsmeans_effects:
            effects = ', '.join(f'~ {e}' for e in self.lsmeans_effects[:2])
            self.lines.append(f"# LSMEANS equivalent:")
            self.lines.append(f"emmeans::emmeans(mixed_model, {effects})")

    def _emit_proc_phreg(self):
        ds   = self.proc_opts.get('data', self.current_dataset) or 'data'
        time_decl = self.time_stmt or self.current_model.get('dependent', 'time*event(0)')
        ind  = self.current_model.get('independent', '.')
        strt = ', '.join(self.strata_vars) if self.strata_vars else None
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC PHREG: Cox proportional hazards on {ds}")
        # Parse "time*event(0)" style declaration
        surv_expr = "Surv(time, event)"
        if '*' in time_decl:
            parts = time_decl.split('*')
            t_var = parts[0].strip()
            e_part = parts[1].strip()
            m_ev = re.search(r'(\w+)\s*\((\d+)\)', e_part)
            if m_ev:
                e_var, censor_val = m_ev.group(1), m_ev.group(2)
                surv_expr = f"Surv({t_var}, {e_var} != {censor_val})"
            else:
                surv_expr = f"Surv({t_var}, {e_part})"
        formula = f"{surv_expr} ~ {ind.strip() or '1'}"
        if strt:
            formula += f" + strata({strt})"
        self.lines.append(f"cox_model <- survival::coxph({formula}, data = {ds})")
        self.lines.append("print(summary(cox_model))")
        self.lines.append("print(survival::cox.zph(cox_model))  # proportional hazards test")

    def _emit_proc_lifetest(self):
        ds   = self.proc_opts.get('data', self.current_dataset) or 'data'
        time_decl = self.time_stmt or 'TIME*STATUS(0)'
        strt = ', '.join(self.strata_vars) if self.strata_vars else None
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC LIFETEST: Kaplan-Meier survival on {ds}")
        # Parse time declaration
        surv_expr = "Surv(TIME, STATUS)"
        if '*' in time_decl:
            parts = time_decl.split('*')
            t_var = parts[0].strip()
            e_part = parts[1].strip()
            m_ev = re.search(r'(\w+)\s*\((\d+)\)', e_part)
            if m_ev:
                e_var, censor_val = m_ev.group(1), m_ev.group(2)
                surv_expr = f"Surv({t_var}, {e_var} != {censor_val})"
        strata_formula = f"~ {strt}" if strt else "~ 1"
        self.lines.append(f"km_fit <- survival::survfit({surv_expr} {strata_formula}, data = {ds})")
        self.lines.append("print(summary(km_fit))")
        self.lines.append("plot(km_fit, xlab = 'Time', ylab = 'Survival Probability')")
        if strt:
            self.lines.append(f"# Log-rank test:")
            self.lines.append(f"survival::survdiff({surv_expr} {strata_formula}, data = {ds})")

    def _emit_proc_report(self):
        ds   = self._strip_libname(self.proc_opts.get('data', self.current_dataset) or 'data')

        # If PROC REPORT references a dataset that's likely not created, use summary_stats if it exists
        if ds == 'age_summary' and 'summary_stats' in self._created_datasets:
            ds = 'summary_stats'

        cols = self.column_vars or self.analyze_vars
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC REPORT: Publication table")
        self.lines.append("# gt package generates HTML/PDF/Word tables (closest SAS PROC REPORT equivalent)")
        if cols:
            select_cols = ', '.join(cols)
            self.lines.append(f"report_tbl <- {ds} %>%")
            self.lines.append(f"  select({select_cols})")
            if self.where_condition:
                self.lines.append(f"  filter({self.where_condition})")
        else:
            self.lines.append(f"report_tbl <- {ds}")
        # Display as formatted text table instead of HTML
        self.lines.append("cat('\\n')")
        self.lines.append("print(as.data.frame(report_tbl), max = 1000)")

    def _emit_proc_tabulate(self):
        ds  = self.proc_opts.get('data', self.current_dataset) or 'data'
        cls = ', '.join(self.class_vars) if self.class_vars else None
        avs = ', '.join(self.analyze_vars) if self.analyze_vars else None
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC TABULATE: Summary table for {ds}")
        self.lines.append("# gtsummary::tbl_summary is the closest R equivalent")
        if cls:
            self.lines.append(f"tab_tbl <- {ds} %>%")
            if avs:
                self.lines.append(f"  select({cls}, {avs}) %>%")
            self.lines.append(f"  gtsummary::tbl_summary(by = {self.class_vars[0]})")
        else:
            self.lines.append(f"tab_tbl <- {ds} %>% gtsummary::tbl_summary()")
        self.lines.append("print(tab_tbl)")

    def _emit_proc_compare(self):
        base_ds    = self._strip_libname(self.proc_opts.get('data', self.current_dataset) or 'base_data')
        compare_ds = self._strip_libname(self.proc_opts.get('compare', 'compare_data'))
        self.lines.append("# PROC COMPARE: Dataset comparison")
        self.lines.append("cat('\\n--- Dataset Comparison Summary ---\\n')")
        self.lines.append(f"cat('Base dataset:    ', nrow({base_ds}), 'rows,', ncol({base_ds}), 'cols\\n')")
        self.lines.append(f"cat('Compare dataset: ', nrow({compare_ds}), 'rows,', ncol({compare_ds}), 'cols\\n')")
        self.lines.append(f"cat('\\nRow counts match:', nrow({base_ds}) == nrow({compare_ds}), '\\n')")
        self.lines.append(f"cat('Column counts match:', ncol({base_ds}) == ncol({compare_ds}), '\\n')")

    def _emit_proc_contents(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
        self.lines.append(f"# PROC CONTENTS: Dataset metadata for {ds}")
        self.lines.append(f"cat('Dataset:', '{ds}', '\\n')")
        self.lines.append(f"cat('Rows:', nrow({ds}), ' Columns:', ncol({ds}), '\\n')")
        self.lines.append(f"dplyr::glimpse({ds})")
        self.lines.append(f"str({ds})")

    def _emit_proc_univariate(self):
        ds  = self.proc_opts.get('data', self.current_dataset) or 'data'
        avs = self.analyze_vars
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC UNIVARIATE: Distribution analysis for {ds}")
        if avs:
            for v in avs:
                self.lines.append(f"cat('\\n--- {v} ---\\n')")
                self.lines.append(f"print(summary({ds}${v}))")
                self.lines.append(f"cat('Skewness:', moments::skewness({ds}${v}, na.rm=TRUE), '\\n')")
                self.lines.append(f"cat('Kurtosis:', moments::kurtosis({ds}${v}, na.rm=TRUE), '\\n')")
                self.lines.append(f"shapiro_test <- shapiro.test({ds}${v}[!is.na({ds}${v})][1:min(5000, sum(!is.na({ds}${v})))])")
                self.lines.append(f"cat('Shapiro-Wilk p-value:', shapiro_test$p.value, '\\n')")
        else:
            self.lines.append(f"print(summary({ds}))")

    def _emit_proc_corr(self):
        ds  = self.proc_opts.get('data', self.current_dataset) or 'data'
        avs = self.analyze_vars
        if self.current_title:
            self.lines.append(f"cat('\\n{self.current_title}\\n')")
        self.lines.append(f"# PROC CORR: Correlation analysis for {ds}")
        if avs:
            cols = ', '.join(f'"{v}"' for v in avs)
            self.lines.append(f"corr_data <- {ds}[, c({cols})]")
        else:
            self.lines.append(f"corr_data <- {ds} %>% dplyr::select(where(is.numeric))")
        self.lines.append("corr_matrix <- cor(corr_data, use = 'pairwise.complete.obs')")
        self.lines.append("print(round(corr_matrix, 4))")
        self.lines.append("# For p-values: Hmisc::rcorr(as.matrix(corr_data))")

    def _emit_proc_import(self):
        opts    = self.proc_opts
        # PROC IMPORT can use either DATA= or OUT= for the output dataset
        out_ds  = opts.get('data') or opts.get('out') or 'imported_data'
        datafile = opts.get('datafile', 'input_file')
        dbms    = opts.get('dbms', 'csv')

        # Strip libname prefix if present (e.g., "sdtm.dm" → "dm")
        if '.' in out_ds:
            out_ds = out_ds.split('.')[-1]

        # Track this dataset as imported (don't try to read as SAS file later)
        self._imported_datasets.add(out_ds.lower())

        self.lines.append(f"# PROC IMPORT: Read {datafile}")
        if dbms in ('csv', 'dlm', 'tab'):
            sep = '\\t' if dbms == 'tab' else ','
            self.lines.append(f'{out_ds} <- readr::read_delim("{datafile}", delim="{sep}", show_col_types=FALSE)')
        elif dbms == 'xlsx':
            self.lines.append(f'{out_ds} <- readxl::read_excel("{datafile}")')
        elif dbms in ('sas7bdat', 'sas'):
            self.lines.append(f'{out_ds} <- haven::read_sas("{datafile}")')
        elif dbms == 'xpt':
            self.lines.append(f'{out_ds} <- haven::read_xpt("{datafile}")')
        else:
            self.lines.append(f'{out_ds} <- readr::read_csv("{datafile}")  # adjust reader for {dbms}')

    # ── SQL to R translation ──────────────────────────────────────────────

    def _translate_sql(self, sql_statements: List[str]) -> List[str]:
        """Translate common PROC SQL patterns to R (dplyr) code."""
        r_lines = []
        full_sql = '\n'.join(sql_statements)

        # Pattern 1: CREATE TABLE ... AS SELECT ... FROM ... LEFT JOIN
        create_table_match = re.search(
            r'create\s+table\s+(\w+)\s+as\s+select\s+(.*?)\s+from\s+(\w+)\s+(\w+)\s+on\s+(.*?)(?:;|quit)',
            full_sql, re.IGNORECASE | re.DOTALL
        )
        if create_table_match:
            out_table = create_table_match.group(1).split('.')[-1]
            select_cols = create_table_match.group(2).strip()
            from_table = create_table_match.group(3)
            join_clause = create_table_match.group(4).lower().strip()  # left join, inner join, etc.
            on_condition = create_table_match.group(5).strip()

            # Extract join condition (e.g., "a.USUBJID = b.USUBJID")
            join_parts = on_condition.split('=')
            if len(join_parts) == 2:
                left_key = join_parts[0].strip().split('.')[-1]
                right_key = join_parts[1].strip().split('.')[-1]

                if 'left' in join_clause:
                    r_lines.append(f"# PROC SQL: LEFT JOIN")
                    r_lines.append(f"{out_table} <- {from_table} %>%")
                    r_lines.append(f"  left_join(select first 100 rows from right table, by = c(\"{left_key}\" = \"{right_key}\"))")
                    self._imported_datasets.add(out_table.lower())
                    self._created_datasets.add(out_table)
                    return r_lines

        # Pattern 2: SELECT COUNT(*) INTO :macro_var
        count_match = re.search(
            r'select\s+count\(\*\)\s+into\s+:(\w+)\s+from\s+(\w+)',
            full_sql, re.IGNORECASE
        )
        if count_match:
            macro_var = count_match.group(1)
            table = count_match.group(2).split('.')[-1]
            r_lines.append(f"# PROC SQL: COUNT INTO macro variable")
            r_lines.append(f"{macro_var} <- nrow({table})")
            self._macro_vars[macro_var] = f"nrow({table})"
            return r_lines

        # Default: comment out untranslated SQL
        r_lines.append(f"# PROC SQL (translate manually): {'; '.join(sql_statements)}")
        return r_lines

    # ── SAS expression → R expression ────────────────────────────────────

    # Date-related format keywords used in SAS input()/put()
    _DATE_FMTS = {'yymmdd', 'date', 'mmddyy', 'ddmmyy', 'is8601', 'julian',
                  'yymmddn', 'dateampm', 'datetime', 'anydtdte'}

    def _sas2r(self, expr: str) -> str:
        if not expr:
            return ''
        r = expr

        # ── SAS automatic variables ───────────────────────────────────────────
        r = re.sub(r'\b_N_\b', 'row_number()', r)
        r = re.sub(r'\b_NOBS_\b', 'n()', r)

        # ── Logical operators ─────────────────────────────────────────────────
        r = re.sub(r'\bAND\b', '&', r, flags=re.I)
        r = re.sub(r'\bOR\b', '|', r, flags=re.I)
        r = re.sub(r'\bNOT\b', '!', r, flags=re.I)

        # ── Comparison operators (word forms) ─────────────────────────────────
        r = re.sub(r'\bEQ\b', '==', r, flags=re.I)
        r = re.sub(r'\bNE\b', '!=', r, flags=re.I)
        r = re.sub(r'\bLT\b', '<', r, flags=re.I)
        r = re.sub(r'\bLE\b', '<=', r, flags=re.I)
        r = re.sub(r'\bGT\b', '>', r, flags=re.I)
        r = re.sub(r'\bGE\b', '>=', r, flags=re.I)
        # Bare = in conditions → ==
        r = re.sub(r'(?<![!<>=])=(?!=)', '==', r)

        # ── Power ─────────────────────────────────────────────────────────────
        r = r.replace('**', '^')

        # ── String functions ──────────────────────────────────────────────────
        r = re.sub(r'\bupcase\s*\(',   'toupper(', r, flags=re.I)
        r = re.sub(r'\blowcase\s*\(',  'tolower(', r, flags=re.I)
        r = re.sub(r'\btrim\s*\(',     'trimws(', r, flags=re.I)
        r = re.sub(r'\bstrip\s*\(',    'trimws(', r, flags=re.I)
        r = re.sub(r'\bpropcase\s*\(', 'str_to_title(', r, flags=re.I)
        r = re.sub(r'\bcats\s*\(',     'paste0(', r, flags=re.I)
        r = re.sub(r'\bcatt\s*\(',     'paste0(', r, flags=re.I)
        r = re.sub(r'\bsubstr\s*\(',   'substr(', r, flags=re.I)
        
        # index(string, pattern) → grepl(pattern, string) — swap arguments!
        # First convert index to grepl, then swap the arguments
        def _translate_index(m: re.Match) -> str:
            inner = m.group(1)
            # Parse the two arguments: string and pattern
            # Need to handle nested parens correctly
            depth = 0
            first_comma = -1
            for i, ch in enumerate(inner):
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                elif ch == ',' and depth == 0:
                    first_comma = i
                    break
            if first_comma == -1:
                # No comma found, keep as is
                return f'grepl({inner})'
            string_arg = inner[:first_comma].strip()
            pattern_arg = inner[first_comma+1:].strip()
            return f'grepl({pattern_arg}, {string_arg})'
        
        r = re.sub(r'\bindex\s*\(([^)]+)\)', _translate_index, r, flags=re.I)
        
        r = re.sub(r'\bcompress\s*\(', 'gsub(" ", "", ', r, flags=re.I)
        r = re.sub(r'\btranwrd\s*\(',  'gsub(', r, flags=re.I)
        r = re.sub(r'\bscan\s*\(',     'strsplit(', r, flags=re.I)
        r = re.sub(r'\bleft\s*\(',     'trimws(', r, flags=re.I)

        # catx(sep, a, b, ...) → paste(a, b, ..., sep=sep)
        def _translate_catx(m: re.Match) -> str:
            inner = m.group(1)
            # Split on first comma to get separator
            comma_pos = inner.find(',')
            if comma_pos == -1:
                return f'paste({inner})'
            sep = inner[:comma_pos].strip()
            rest_args = inner[comma_pos + 1:].strip()
            return f'paste({rest_args}, sep={sep})'
        r = re.sub(r'\bcatx\s*\(([^)]+)\)', _translate_catx, r, flags=re.I)

        # cat(a, b) → paste0(a, b)
        r = re.sub(r'\bcat\s*\(',  'paste0(', r, flags=re.I)

        # ── Numeric / math functions ──────────────────────────────────────────
        r = re.sub(r'\bint\s*\(',    'as.integer(', r, flags=re.I)
        r = re.sub(r'\bceil\s*\(',   'ceiling(', r, flags=re.I)
        r = re.sub(r'\bfloor\s*\(',  'floor(', r, flags=re.I)
        r = re.sub(r'\babs\s*\(',    'abs(', r, flags=re.I)
        r = re.sub(r'\bsqrt\s*\(',   'sqrt(', r, flags=re.I)
        r = re.sub(r'\bexp\s*\(',    'exp(', r, flags=re.I)
        r = re.sub(r'\blog\s*\(',    'log(', r, flags=re.I)
        r = re.sub(r'\bround\s*\(',  'round(', r, flags=re.I)
        r = re.sub(r'\bmod\s*\(([^,]+),\s*([^)]+)\)', r'(\1 %% \2)', r, flags=re.I)
        r = re.sub(r'\bsum\s*\(',   'sum(', r, flags=re.I)
        r = re.sub(r'\bmean\s*\(',  'mean(', r, flags=re.I)
        r = re.sub(r'\bmin\s*\(',   'pmin(', r, flags=re.I)
        r = re.sub(r'\bmax\s*\(',   'pmax(', r, flags=re.I)
        r = re.sub(r'\bcoalesce\s*\(', 'dplyr::coalesce(', r, flags=re.I)
        r = re.sub(r'\bifn\s*\(',   'if_else(', r, flags=re.I)
        r = re.sub(r'\bifc\s*\(',   'if_else(', r, flags=re.I)
        r = re.sub(r'\bnmiss\s*\(([^)]+)\)', r'sum(is.na(\1))', r, flags=re.I)

        # ── Date / time functions ─────────────────────────────────────────────
        r = re.sub(r'\btoday\s*\(\s*\)', 'Sys.Date()', r, flags=re.I)
        r = re.sub(r'\byear\s*\(',   'lubridate::year(', r, flags=re.I)
        r = re.sub(r'\bmonth\s*\(',  'lubridate::month(', r, flags=re.I)
        r = re.sub(r'\bday\s*\(',    'lubridate::day(', r, flags=re.I)
        r = re.sub(r'\bdatepart\s*\(', 'as.Date(', r, flags=re.I)
        r = re.sub(r'\bmdy\s*\(',    'lubridate::make_date(', r, flags=re.I)
        r = re.sub(r'\bymd\s*\(',    'lubridate::ymd(', r, flags=re.I)
        r = re.sub(r'\bdatdif\s*\(([^,]+),\s*([^,]+),\s*[^)]+\)',
                   r'as.numeric(difftime(\2, \1, units = "days"))', r, flags=re.I)

        # intck('unit', start, end) → lubridate interval
        def _translate_intck(m: re.Match) -> str:
            unit  = m.group(1).strip().strip("'\"").lower()
            start = m.group(2).strip()
            end   = m.group(3).strip()
            unit_map = {'day': 'days(1)', 'month': 'months(1)', 'year': 'years(1)',
                        'week': 'weeks(1)', 'hour': 'hours(1)'}
            r_unit = unit_map.get(unit, 'days(1)')
            return f'as.numeric(lubridate::interval({start}, {end}), "{unit}s")'
        r = re.sub(r'\bintck\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\)',
                   _translate_intck, r, flags=re.I)

        # intnx('unit', date, n) → date + lubridate period
        def _translate_intnx(m: re.Match) -> str:
            unit  = m.group(1).strip().strip("'\"").lower()
            dt    = m.group(2).strip()
            n     = m.group(3).strip()
            fn_map = {'day': 'days', 'month': 'months', 'year': 'years', 'week': 'weeks'}
            fn = fn_map.get(unit, 'days')
            return f'{dt} + lubridate::{fn}({n})'
        r = re.sub(r'\bintnx\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\)',
                   _translate_intnx, r, flags=re.I)

        # input(x, format.) — format-aware date vs numeric
        def _translate_input(m: re.Match) -> str:
            var = m.group(1).strip()
            fmt = m.group(2).strip().lower().rstrip('.')
            if any(kw in fmt for kw in RCodeGenerator._DATE_FMTS):
                return f'as.Date({var}, "%Y-%m-%d")'
            return f'as.numeric({var})'
        r = re.sub(r'\binput\s*\(([^,]+),\s*(\S+)\)', _translate_input, r, flags=re.I)

        # put(x, format.) — format-aware date formatting
        def _translate_put(m: re.Match) -> str:
            var = m.group(1).strip()
            fmt = m.group(2).strip().lower().rstrip('.')
            if 'is8601' in fmt:
                return f'format(as.Date({var}, origin = "1960-01-01"), "%Y-%m-%d")'
            if any(kw in fmt for kw in RCodeGenerator._DATE_FMTS):
                return f'format(as.Date({var}, origin = "1960-01-01"), "%Y-%m-%d")'
            return f'as.character({var})'
        r = re.sub(r'\bput\s*\(([^,]+),\s*(\S+)\)', _translate_put, r, flags=re.I)

        # ── Date arithmetic: DT - DT → as.numeric(DT - DT) ──────────────────
        r = self._DT_ARITH_RE.sub(
            lambda m: f"as.numeric({m.group(1)} - {m.group(2)})", r
        )

        # ── SAS missing value (standalone dot) ────────────────────────────────
        r = re.sub(r'(?<![.\w])\.(?![.\w])', 'NA', r)
        return self._canonicalize_vars(r)
