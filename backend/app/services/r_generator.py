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
                 inline_data: Optional[List[Any]] = None) -> str:
        self._reset_state()
        self.inline_data = inline_data or []
        self.inline_data_idx = 0
        self._emit_header()
        for node in ast:
            self._process(node)
        return '\n'.join(self.lines)

    # ── state helpers ─────────────────────────────────────────────────────

    def _reset_state(self):
        self.lines: List[str] = []
        self.inline_data: List[Any] = []
        self.inline_data_idx: int = 0
        # current context
        self.current_proc: Optional[str] = None
        self.current_dataset: Optional[str] = None
        self.proc_opts: Dict[str, str] = {}
        self.stat_opts: List[str] = []
        self.input_vars: List[Dict[str, str]] = []
        self.analyze_vars: List[str] = []
        self.class_vars: List[str] = []
        self.by_vars: List[str] = []
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

    def _reset_proc_ctx(self):
        self.proc_opts = {}
        self.stat_opts = []
        self.analyze_vars = []
        self.class_vars = []
        self.by_vars = []
        self.by_desc = False
        self.by_var_desc: List[bool] = []
        self.table_vars = []
        self.current_model = {}
        self.current_means_stmt = {}
        self.current_title = None
        self.where_condition: Optional[str] = None
        self.data_has_set = False

    # ── node dispatcher ───────────────────────────────────────────────────

    def _process(self, node: Dict[str, Any]):
        t = node.get('type', '')

        if t == 'data_step':
            self.current_dataset = node.get('dataset', 'data')
            self.current_proc = 'data'
            self.input_vars = []
            self.data_step_active = False
            self.pending_data_ops = []
            self.pending_post_data_ops = []
            self._reset_proc_ctx()

        elif t == 'set':
            datasets = node.get('datasets') or [node.get('dataset', 'data')]
            if len(datasets) > 1:
                self.lines.append(f"{self.current_dataset} <- bind_rows({', '.join(datasets)})")
            else:
                self.lines.append(f"{self.current_dataset} <- {datasets[0]}")
            self.data_has_set = True

        elif t == 'input':
            self.input_vars = node.get('variables', [])

        elif t == 'length':
            self.lines.append(f"# LENGTH: {node.get('declaration', '')}")

        elif t == 'datalines':
            self.data_step_active = True

        elif t == 'assignment':
            self._emit_assignment(node)

        elif t == 'if_statement':
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
                                       ['n', 'mean', 'std', 'min', 'max'])
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
            self.lines.append("# PROC SQL – translate manually or use dplyr joins")

        elif t == 'proc_fcmp':
            self._flush_if_chain()
            self.current_proc = 'proc_fcmp'
            self.lines.append("# PROC FCMP – define equivalent R function(s) below")

        elif t == 'proc_transpose':
            self._flush_if_chain()
            self.current_proc = 'proc_transpose'
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

        elif t == 'by':
            self.by_vars = node.get('variables', [])
            self.by_desc = node.get('descending', False)
            self.by_var_desc = node.get('var_descending', [])

        elif t in ('run', 'quit'):
            self._flush_if_chain()
            self._handle_run()

        elif t == 'unknown':
            stmt = node.get('statement', '').strip()
            if stmt:
                self.lines.append(f"# TODO: Untranslated SAS statement: {stmt}")

    # ── RUN handler – deferred emit ───────────────────────────────────────

    def _handle_run(self):
        if self.current_proc == 'data':
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
                self._emit_info_print(self.current_dataset)
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

        self.lines.append('')
        self.current_proc = None
        self._reset_proc_ctx()

    # ── emitters ──────────────────────────────────────────────────────────

    def _emit_header(self):
        self.lines += [
            "# Auto-generated R code from SAS",
            "# Generated by SAS to R Automation Platform",
            "",
            "library(dplyr)",
            "library(tidyr)",
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
        self.lines.append(f"print(as.data.frame({ds}), row.names = FALSE)")
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
        self.lines.append(f"print(as.data.frame({ds}), row.names = FALSE)")

    def _emit_assignment(self, node: Dict[str, Any]):
        var = node.get('variable', '')
        expr = self._sas2r(node.get('expression', ''))
        if self.current_proc == 'data' and self.current_dataset:
            self.pending_data_ops.append(f"{self.current_dataset} <- {self.current_dataset} %>%")
            self.pending_data_ops.append(f"  mutate({var} = {expr})")
        else:
            self.lines.append(f"{var} <- {expr}")

    def _emit_if(self, node: Dict[str, Any]):
        cond = self._sas2r(node.get('condition', ''))
        then = node.get('then_clause') or ''
        else_ = node.get('else_clause')
        ds = self.current_dataset

        if ds and '=' in then:
            var = then.split('=')[0].strip()
            tv = then.split('=', 1)[1].strip().replace("'", '"')
            op_lines = [
                f"{ds} <- {ds} %>%",
                f"  mutate({var} = case_when(",
                f"    {cond} ~ {tv},",
            ]
            if else_ and '=' in else_:
                ev = else_.split('=', 1)[1].strip().replace("'", '"')
                op_lines.append(f"    TRUE ~ {ev}")
            else:
                op_lines.append("    TRUE ~ NA_character_")
            op_lines.append("  ))")
            if self.current_proc == 'data':
                self.pending_data_ops.extend(op_lines)
            else:
                self.lines.extend(op_lines)

    def _start_if_chain(self, node: Dict[str, Any]):
        self.pending_if_chain = [node]

    def _extend_if_chain(self, node: Dict[str, Any]):
        if not self.pending_if_chain:
            self.pending_if_chain = [node]
            return
        self.pending_if_chain.append(node)

    def _close_if_chain_with_else(self, node: Dict[str, Any]):
        if not self.pending_if_chain:
            self.pending_if_chain = [node]
            return
        self.pending_if_chain.append(node)
        self._flush_if_chain()

    def _flush_if_chain(self):
        if not self.pending_if_chain or not self.current_dataset:
            self.pending_if_chain = []
            return

        first_assign = None
        cases = []
        default_val = "NA_character_"

        for n in self.pending_if_chain:
            t = n.get('type')
            if t in ('if_statement', 'else_if_statement'):
                cond = self._sas2r(n.get('condition', ''))
                clause = (n.get('then_clause') or '').strip()
                if '=' in clause:
                    var, val = clause.split('=', 1)
                    var = var.strip()
                    val = val.strip().replace("'", '"')
                    if first_assign is None:
                        first_assign = var
                    if var == first_assign:
                        cases.append((cond, val))
            elif t == 'else_statement':
                clause = (n.get('clause') or '').strip()
                if '=' in clause:
                    var, val = clause.split('=', 1)
                    var = var.strip()
                    val = val.strip().replace("'", '"')
                    if first_assign is None:
                        first_assign = var
                    if var == first_assign:
                        default_val = val

        if first_assign and cases:
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
            self.lines.append("# TODO: Could not fully translate IF/ELSE IF/ELSE chain.")

        self.pending_if_chain = []

    def _emit_where(self, node: Dict[str, Any]):
        cond = self._sas2r(node.get('condition', ''))
        if self.current_proc == 'data' and self.current_dataset:
            self.pending_data_ops.append(f"{self.current_dataset} <- {self.current_dataset} %>%")
            self.pending_data_ops.append(f"  filter({cond})")
        else:
            # Store for use in the proc emitter; avoids permanently mutating the dataset
            self.where_condition = cond

    def _emit_keep(self, node: Dict[str, Any]):
        vs = node.get('variables', [])
        if self.current_dataset and vs:
            op_lines = [
                f"{self.current_dataset} <- {self.current_dataset} %>%",
                f"  select({', '.join(vs)})",
            ]
            if self.current_proc == 'data':
                self.pending_data_ops.extend(op_lines)
            else:
                self.lines.extend(op_lines)

    def _emit_drop(self, node: Dict[str, Any]):
        vs = node.get('variables', [])
        if self.current_dataset and vs:
            drop = ', '.join(f'-{v}' for v in vs)
            op_lines = [
                f"{self.current_dataset} <- {self.current_dataset} %>%",
                f"  select({drop})",
            ]
            if self.current_proc == 'data':
                self.pending_data_ops.extend(op_lines)
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
            self.lines.append(f"# TODO: Review PUT statement translation: put {content};")

    def _emit_proc_means(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
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
        # Default order matches SAS PROC MEANS default: N Mean StdDev Min Max
        use_stats = [s for s in self.stat_opts if s in stat_map] or \
                    ['n', 'mean', 'std', 'min', 'max']
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
        self.lines.append("print(as.data.frame(summary_stats), row.names = FALSE)")

    def _emit_proc_freq(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
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
                self.lines.append(f"print(as.data.frame(freq_{safe}), row.names = FALSE)")
            else:
                self.lines += [
                    f"freq_{safe} <- {ds} %>%",
                    f"  count({var}) %>%",
                    "  mutate(",
                    "    Percent = round(n / sum(n) * 100, 2),",
                    "    CumFreq = cumsum(n),",
                    "    CumPercent = cumsum(Percent)",
                    "  )",
                ]
                self.lines.append(f"cat(sprintf('\\nFrequency Table for {var}\\n'))")
                self.lines.append(f"print(as.data.frame(freq_{safe}), row.names = FALSE)")
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
            self.lines.append(
                f"cat(sprintf('NOTE: There were %d observations read from {ds.upper()}.\\n', nrow({ds})))")
            self.lines.append(
                f"cat(sprintf('NOTE: Dataset {out.upper()} has %d observations and %d variables.\\n', nrow({out}), ncol({out})))")
            self.lines.append(f"print(as.data.frame({out}), row.names = FALSE)")
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
            self.lines.append(f"print(as.data.frame({ds_ref}[, c({cols}), drop = FALSE]), row.names = FALSE)")
        else:
            self.lines.append(f"print(as.data.frame({ds_ref}), row.names = FALSE)")

    def _emit_proc_transpose(self):
        ds = self.proc_opts.get('data', self.current_dataset) or 'data'
        out = self.proc_opts.get('out', ds + '_t')
        self.lines += [
            f"# PROC TRANSPOSE: Pivot {ds}",
            f"# Convert long↔wide using tidyr::pivot_wider / pivot_longer",
            f"{out} <- {ds} %>%",
            f"  pivot_wider(names_from = 1, values_from = 2)  # adjust columns",
            f"print(as.data.frame({out}), row.names = FALSE)",
        ]

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

    # ── SAS expression → R expression ────────────────────────────────────

    def _sas2r(self, expr: str) -> str:
        if not expr:
            return ''
        r = expr
        # logical operators
        r = re.sub(r'\bAND\b', '&', r, flags=re.I)
        r = re.sub(r'\bOR\b', '|', r, flags=re.I)
        r = re.sub(r'\bNOT\b', '!', r, flags=re.I)
        # comparison operators (word forms)
        r = re.sub(r'\bEQ\b', '==', r, flags=re.I)
        r = re.sub(r'\bNE\b', '!=', r, flags=re.I)
        r = re.sub(r'\bLT\b', '<', r, flags=re.I)
        r = re.sub(r'\bLE\b', '<=', r, flags=re.I)
        r = re.sub(r'\bGT\b', '>', r, flags=re.I)
        r = re.sub(r'\bGE\b', '>=', r, flags=re.I)
        # SAS uses = for equality in conditions; R uses ==
        # Only replace bare = that is not already part of <=, >=, !=, ==
        r = re.sub(r'(?<![!<>=])=(?!=)', '==', r)
        # power
        r = r.replace('**', '^')
        # SAS functions → R
        r = re.sub(r'\bint\s*\(', 'as.integer(', r, flags=re.I)
        r = re.sub(r'\bupcase\s*\(', 'toupper(', r, flags=re.I)
        r = re.sub(r'\blowcase\s*\(', 'tolower(', r, flags=re.I)
        r = re.sub(r'\btrim\s*\(', 'trimws(', r, flags=re.I)
        r = re.sub(r'\bcats\s*\(', 'paste0(', r, flags=re.I)
        r = re.sub(r'\bsubstr\s*\(', 'substr(', r, flags=re.I)
        r = re.sub(r'\binput\s*\(([^,]+),\s*\S+\)', r'as.numeric(\1)', r, flags=re.I)
        r = re.sub(r'\bput\s*\(([^,]+),\s*\S+\)', r'as.character(\1)', r, flags=re.I)
        r = re.sub(r'\babs\s*\(', 'abs(', r, flags=re.I)
        r = re.sub(r'\bsqrt\s*\(', 'sqrt(', r, flags=re.I)
        r = re.sub(r'\bexp\s*\(', 'exp(', r, flags=re.I)
        r = re.sub(r'\blog\s*\(', 'log(', r, flags=re.I)
        r = re.sub(r'\bround\s*\(', 'round(', r, flags=re.I)
        r = re.sub(r'\bmod\s*\(([^,]+),\s*([^)]+)\)', r'(\1 %% \2)', r, flags=re.I)
        # SAS missing value (standalone dot)
        r = re.sub(r'(?<![.\w])\.(?![.\w])', 'NA', r)
        return r
