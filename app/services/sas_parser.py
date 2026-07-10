"""
SAS Parser
Parses SAS code into an Abstract Syntax Tree with proper DATALINES support.
"""

import re
from typing import Dict, List, Any, Optional, Tuple


class SASParser:
    """
    Parses SAS code into an AST plus extracted inline data (DATALINES).
    Supports: DATA steps, PROC MEANS/FREQ/SORT/PRINT/SQL, IF-THEN-ELSE,
              assignments, WHERE, KEEP, DROP, BY, VAR, CLASS, TABLES.
    """

    def parse(self, code: str) -> Tuple[List[Dict[str, Any]], List[Any]]:
        """
        Parse SAS code.

        Returns:
            (statements, inline_data) where inline_data is a list of rows
            parsed from the most recent DATALINES block.
        """
        statements: List[Dict[str, Any]] = []
        inline_blocks: List[List[List[str]]] = []
        current_stmt_lines: List[str] = []
        in_datalines = False
        in_block_comment = False
        data_rows: List[List[str]] = []

        for raw_line in code.split('\n'):
            line = raw_line.strip()

            # ── block comments ────────────────────────────────────────────
            if in_block_comment:
                if '*/' in line:
                    in_block_comment = False
                continue

            if '/*' in line:
                before = line[:line.index('/*')]
                after_close = ''
                if '*/' in line:
                    after_close = line[line.index('*/') + 2:]
                else:
                    in_block_comment = True
                line = (before + after_close).strip()
                if not line:
                    continue

            # ── inside DATALINES / CARDS block ────────────────────────────
            if in_datalines:
                if line == ';':                       # terminating lone ;
                    in_datalines = False
                    inline_blocks.append([r for r in data_rows])
                elif line:
                    data_rows.append(line.split())
                continue

            # ── skip blank lines and single-line SAS comments (* …; ) ─────
            if not line:
                continue
            if line.startswith('*') and ';' in line:
                continue

            current_stmt_lines.append(line)

            if ';' not in line:
                continue

            # ── one or more semicolons found – split into statements ───────
            full = ' '.join(current_stmt_lines)
            current_stmt_lines = []

            for part in self._split_semicolons(full):
                part = part.strip()
                if not part:
                    continue
                node = self._parse_statement(part)
                if node:
                    statements.append(node)
                    if node.get('type') == 'datalines':
                        in_datalines = True
                        data_rows = []
                        break           # rest of accumulated text is data

        return statements, inline_blocks

    # ── internal helpers ──────────────────────────────────────────────────

    def _split_semicolons(self, text: str) -> List[str]:
        """Split on semicolons, respecting quoted strings."""
        parts: List[str] = []
        cur: List[str] = []
        in_str = False
        str_char = ''
        for ch in text:
            if in_str:
                cur.append(ch)
                if ch == str_char:
                    in_str = False
            elif ch in ('"', "'"):
                in_str = True
                str_char = ch
                cur.append(ch)
            elif ch == ';':
                parts.append(''.join(cur).strip())
                cur = []
            else:
                cur.append(ch)
        if cur:
            parts.append(''.join(cur).strip())
        return parts

    def _parse_statement(self, stmt: str) -> Optional[Dict[str, Any]]:
        lo = stmt.lower().strip()

        # LIBNAME
        if lo.startswith('libname '):
            parts = stmt.split(None, 3)
            libref = parts[1].lower() if len(parts) > 1 else 'unknown'
            path = parts[2].strip('"\'') if len(parts) > 2 else ''
            return {'type': 'libname', 'libref': libref, 'path': path}

        # DATA step  (but NOT 'datalines')
        if lo.startswith('data ') and not lo.startswith('datalines'):
            parts = stmt.split()
            raw = parts[1] if len(parts) > 1 else 'work'
            lib, name = ('work', raw) if '.' not in raw else raw.split('.', 1)
            # Normalise to lowercase so simulator/generator lookups are case-insensitive
            return {'type': 'data_step', 'dataset': name.lower(), 'library': lib.lower()}

        # MERGE
        if lo.startswith('merge '):
            datasets = self._parse_dataset_list(stmt[6:].strip())
            return {'type': 'merge', 'datasets': datasets}

        # SET
        if lo.startswith('set '):
            datasets = self._parse_dataset_list(stmt[4:].strip())
            names = [d['name'] for d in datasets]
            full_names = [d['full_name'] for d in datasets]
            if not names:
                names = ['unknown']
                full_names = ['unknown']
            return {
                'type': 'set',
                'datasets': names,
                'full_datasets': full_names,
                'dataset': names[0],
            }

        # ARRAY definition  (array arr{n} v1 v2 … or array arr{*} v1-v3)
        if lo.startswith('array '):
            raw = stmt[6:].strip()
            m = re.match(r'(\w+)\s*[{\(](\*|\d+)[}\)]\s*(.*)', raw, re.I)
            if m:
                arr_name = m.group(1)
                arr_size_raw = m.group(2)
                vars_raw = m.group(3).strip()
                # Expand SAS range notation x1-x5 → [x1, x2, x3, x4, x5]
                variables = self._expand_var_list(vars_raw)
                return {
                    'type': 'array_def',
                    'name': arr_name,
                    'size': arr_size_raw,
                    'variables': variables,
                }
            return {'type': 'unknown', 'statement': stmt}

        # DO loop  (indexed: do i = 1 to n; or do i = n to 1 by -1;)
        if lo.startswith('do ') and '=' in lo:
            m = re.match(
                r'do\s+(\w+)\s*=\s*([^;]+?)\s+to\s+([^;]+?)(?:\s+by\s+([^;]+?))?$',
                lo.rstrip(';').strip(), re.I,
            )
            if m:
                return {
                    'type': 'do_loop',
                    'var': m.group(1),
                    'from_val': m.group(2).strip(),
                    'to_val': m.group(3).strip(),
                    'by_val': (m.group(4) or '1').strip(),
                }

        # DO WHILE / DO UNTIL
        if lo.startswith('do while') or lo.startswith('do until'):
            m = re.match(r'do\s+(while|until)\s*\((.+)\)', lo.rstrip(';').strip(), re.I)
            if m:
                return {
                    'type': 'do_while',
                    'kind': m.group(1).lower(),
                    'condition': m.group(2).strip(),
                }

        # DO (plain begin-block — must come AFTER indexed/while forms)
        if lo == 'do':
            return {'type': 'do_block_start'}

        # END
        if lo == 'end':
            return {'type': 'do_block_end'}

        # FORMAT (SAS display format — mark as no-op in R)
        if lo.startswith('format '):
            return {'type': 'format_stmt', 'declaration': stmt[7:].strip()}

        # INPUT
        if lo.startswith('input '):
            return {'type': 'input', 'variables': self._parse_input_vars(stmt[6:].strip())}

        # LENGTH (schema/type declaration)
        if lo.startswith('length '):
            return {'type': 'length', 'declaration': stmt[7:].strip()}

        # DATALINES / CARDS
        if lo in ('datalines', 'cards'):
            return {'type': 'datalines'}

        # PROC MEANS
        if lo.startswith('proc means'):
            return {
                'type': 'proc_means',
                'options': self._proc_opts(stmt),
                'stat_options': self._stat_opts(stmt),
            }

        # PROC FREQ
        if lo.startswith('proc freq'):
            return {'type': 'proc_freq', 'options': self._proc_opts(stmt)}

        # PROC SORT
        if lo.startswith('proc sort'):
            return {'type': 'proc_sort', 'options': self._proc_opts(stmt)}

        # PROC PRINT
        if lo.startswith('proc print'):
            return {'type': 'proc_print', 'options': self._proc_opts(stmt)}

        # PROC SQL
        if lo.startswith('proc sql'):
            return {'type': 'proc_sql', 'options': self._proc_opts(stmt)}

        # PROC TRANSPOSE
        if lo.startswith('proc transpose'):
            return {'type': 'proc_transpose', 'options': self._proc_opts(stmt)}

        # PROC FCMP
        if lo.startswith('proc fcmp'):
            return {'type': 'proc_fcmp', 'options': self._proc_opts(stmt)}

        # PROC REG
        if lo.startswith('proc reg'):
            return {'type': 'proc_reg', 'options': self._proc_opts(stmt)}

        # PROC GLM
        if lo.startswith('proc glm'):
            return {'type': 'proc_glm', 'options': self._proc_opts(stmt)}

        # PROC LOGISTIC
        if lo.startswith('proc logistic'):
            return {'type': 'proc_logistic', 'options': self._proc_opts(stmt)}

        # PROC MIXED
        if lo.startswith('proc mixed'):
            return {'type': 'proc_mixed', 'options': self._proc_opts(stmt)}

        # PROC PHREG
        if lo.startswith('proc phreg'):
            return {'type': 'proc_phreg', 'options': self._proc_opts(stmt)}

        # PROC LIFETEST
        if lo.startswith('proc lifetest'):
            return {'type': 'proc_lifetest', 'options': self._proc_opts(stmt)}

        # PROC REPORT
        if lo.startswith('proc report'):
            return {'type': 'proc_report', 'options': self._proc_opts(stmt)}

        # PROC TABULATE
        if lo.startswith('proc tabulate'):
            return {'type': 'proc_tabulate', 'options': self._proc_opts(stmt)}

        # PROC COMPARE
        if lo.startswith('proc compare'):
            opts = self._proc_opts(stmt)
            m_comp = re.search(r'compare\s*=\s*(\S+)', stmt, flags=re.I)
            if m_comp:
                opts['compare'] = m_comp.group(1).split('.')[-1].lower()
            return {'type': 'proc_compare', 'options': opts}

        # PROC CONTENTS
        if lo.startswith('proc contents'):
            return {'type': 'proc_contents', 'options': self._proc_opts(stmt)}

        # PROC UNIVARIATE
        if lo.startswith('proc univariate'):
            return {'type': 'proc_univariate', 'options': self._proc_opts(stmt)}

        # PROC CORR
        if lo.startswith('proc corr'):
            return {'type': 'proc_corr', 'options': self._proc_opts(stmt)}

        # PROC IMPORT
        if lo.startswith('proc import'):
            opts = self._proc_opts(stmt)
            m_file = re.search(r'datafile\s*=\s*(".*?"|\'.*?\'|\S+)', stmt, flags=re.I)
            m_dbms = re.search(r'dbms\s*=\s*(\w+)', stmt, flags=re.I)
            if m_file:
                opts['datafile'] = m_file.group(1).strip().strip('"').strip("'")
            if m_dbms:
                opts['dbms'] = m_dbms.group(1).lower()
            return {'type': 'proc_import', 'options': opts}

        # PROC EXPORT
        if lo.startswith('proc export'):
            opts = self._proc_opts(stmt)
            m_out = re.search(r'outfile\s*=\s*(".*?"|\'.*?\'|\S+)', stmt, flags=re.I)
            m_dbms = re.search(r'dbms\s*=\s*(\w+)', stmt, flags=re.I)
            if m_out:
                opts['outfile'] = m_out.group(1).strip().strip('"').strip("'")
            if m_dbms:
                opts['dbms'] = m_dbms.group(1).lower()
            return {'type': 'proc_export', 'options': opts}

        # VAR
        if lo.startswith('var '):
            return {'type': 'var', 'variables': stmt[4:].strip().split()}

        # RANDOM (PROC MIXED)
        if lo.startswith('random '):
            raw = stmt[7:].strip()
            left = raw.split('/')[0].strip() if '/' in raw else raw
            opts_part = raw.split('/', 1)[1].strip() if '/' in raw else ''
            return {
                'type': 'random',
                'variables': left.split(),
                'options': opts_part,
            }

        # REPEATED (PROC MIXED)
        if lo.startswith('repeated '):
            return {'type': 'repeated', 'declaration': stmt[9:].strip()}

        # STRATA (PROC LIFETEST / PROC PHREG)
        if lo.startswith('strata '):
            raw = stmt[7:].strip()
            if '/' in raw:
                raw = raw[:raw.index('/')].strip()
            return {'type': 'strata', 'variables': raw.split()}

        # TIME (PROC LIFETEST / PROC PHREG)
        if lo.startswith('time '):
            return {'type': 'time_stmt', 'declaration': stmt[5:].strip()}

        # COLUMN (PROC REPORT / PROC TABULATE)
        if lo.startswith('column '):
            return {'type': 'column', 'variables': stmt[7:].strip().split()}

        # LSMEANS (PROC MIXED / PROC GLM)
        if lo.startswith('lsmeans '):
            raw = stmt[8:].strip()
            effect = raw.split('/')[0].strip()
            opts_part = raw.split('/', 1)[1].strip() if '/' in raw else ''
            return {'type': 'lsmeans', 'effect': effect, 'options': opts_part}

        # HAZARDRATIO (PROC PHREG)
        if lo.startswith('hazardratio '):
            return {'type': 'hazardratio', 'declaration': stmt[12:].strip()}

        # ESTIMATE (PROC MIXED)
        if lo.startswith('estimate '):
            return {'type': 'estimate_stmt', 'declaration': stmt[9:].strip()}

        # CONTRAST (PROC MIXED / PROC GLM)
        if lo.startswith('contrast '):
            return {'type': 'contrast', 'declaration': stmt[9:].strip()}

        # ODS (output delivery — no-op in R, just annotate)
        if lo.startswith('ods '):
            return {'type': 'ods_stmt', 'declaration': stmt[4:].strip()}

        # INFORMAT
        if lo.startswith('informat '):
            return {'type': 'informat_stmt', 'declaration': stmt[9:].strip()}

        # ATTRIB
        if lo.startswith('attrib '):
            return {'type': 'attrib_stmt', 'declaration': stmt[7:].strip()}

        # LABEL
        if lo.startswith('label '):
            return {'type': 'label_stmt', 'declaration': stmt[6:].strip()}

        # RENAME
        if lo.startswith('rename '):
            # rename old=new old2=new2
            pairs: Dict[str, str] = {}
            for m in re.finditer(r'(\w+)\s*=\s*(\w+)', stmt[7:]):
                pairs[m.group(1)] = m.group(2)
            return {'type': 'rename', 'pairs': pairs}

        # BY  (supports per-variable DESCENDING, e.g.: BY Region DESCENDING Revenue)
        if lo.startswith('by '):
            rest = stmt[3:].strip()
            tokens = rest.split()
            var_names: List[str] = []
            var_desc: List[bool] = []
            desc_next = False
            for tok in tokens:
                if tok.lower() == 'descending':
                    desc_next = True
                else:
                    var_names.append(tok)
                    var_desc.append(desc_next)
                    desc_next = False
            return {
                'type': 'by',
                'variables': var_names,
                'descending': any(var_desc),       # backward compat
                'var_descending': var_desc,
            }

        # CLASS
        if lo.startswith('class '):
            return {'type': 'class', 'variables': stmt[6:].strip().split()}

        # TABLES
        if lo.startswith('tables '):
            raw = stmt[7:].strip()
            if '/' in raw:
                raw = raw[:raw.index('/')].strip()
            return {'type': 'tables', 'variables': raw.split()}

        # WHERE
        if lo.startswith('where '):
            return {'type': 'where', 'condition': stmt[6:].strip()}

        # KEEP
        if lo.startswith('keep '):
            return {'type': 'keep', 'variables': stmt[5:].strip().split()}

        # DROP
        if lo.startswith('drop '):
            return {'type': 'drop', 'variables': stmt[5:].strip().split()}

        # PUT (log/output statements inside DATA step)
        if lo.startswith('put '):
            return {'type': 'put', 'content': stmt[4:].strip()}

        # OUTPUT statement
        if lo == 'output':
            return {'type': 'output'}

        # RETAIN
        if lo.startswith('retain '):
            raw = stmt[7:].strip()
            # Collect var=init pairs: "retain cumsum 0 flag 0" → {cumsum: 0, flag: 0}
            tokens = raw.split()
            pairs: Dict[str, str] = {}
            i = 0
            while i < len(tokens):
                tok = tokens[i]
                # If next token looks like a number or literal, pair them
                if i + 1 < len(tokens):
                    nxt = tokens[i + 1]
                    try:
                        float(nxt)
                        pairs[tok] = nxt
                        i += 2
                        continue
                    except ValueError:
                        pass
                pairs[tok] = '0'  # default init
                i += 1
            return {'type': 'retain', 'variables': list(pairs.keys()), 'init_values': pairs}

        # ID statement (PROC TRANSPOSE — column used as variable name)
        if lo.startswith('id ') and not lo.startswith('if '):
            return {'type': 'id_stmt', 'variable': stmt[3:].strip()}

        # IF-THEN-ELSE
        if lo.startswith('if '):
            return self._parse_if(stmt)
        if lo.startswith('else if '):
            return self._parse_else_if(stmt)
        if lo.startswith('else '):
            return self._parse_else(stmt)

        # TITLE
        if lo.startswith('title '):
            return {'type': 'title', 'text': stmt[6:].strip().strip('"').strip("'")}

        # MODEL (PROC GLM)
        if lo.startswith('model '):
            expr = stmt[6:].strip()
            if '=' in expr:
                lhs, rhs = expr.split('=', 1)
                return {'type': 'model', 'dependent': lhs.strip(), 'independent': rhs.strip()}
            return {'type': 'model', 'expression': expr}

        # MEANS statement (PROC GLM style)
        if lo.startswith('means '):
            raw = stmt[6:].strip()
            left = raw
            options = []
            if '/' in raw:
                left, right = raw.split('/', 1)
                options = [x.strip().lower() for x in right.split() if x.strip()]
            return {'type': 'means_stmt', 'variables': [v for v in left.split() if v], 'options': options}

        # RUN / QUIT
        if lo in ('run', 'quit'):
            return {'type': lo}

        # Assignment  (lhs = rhs, no spaces in lhs)
        if '=' in stmt:
            eq = stmt.index('=')
            lhs = stmt[:eq].strip()
            rhs = stmt[eq + 1:].strip()
            if lhs and ' ' not in lhs and not lo.startswith(('proc', 'data', 'set')):
                return {'type': 'assignment', 'variable': lhs, 'expression': rhs}

        return {'type': 'unknown', 'statement': stmt}

    # ── helpers ───────────────────────────────────────────────────────────

    def _parse_input_vars(self, text: str) -> List[Dict[str, str]]:
        """Parse INPUT variables.  Handles 'ID $ Age Gender $ Salary' style."""
        variables = []
        tokens = text.split()
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            # standalone $ → mark preceding variable as character
            if tok == '$':
                if variables:
                    variables[-1]['type'] = 'character'
                i += 1
                continue
            # column pointers / numeric positions
            if tok.startswith('@') or tok.startswith('+') or tok.isdigit():
                i += 1
                continue
            # skip option-like tokens (contain =)
            if '=' in tok:
                i += 1
                continue
            # var$ suffix
            if tok.endswith('$'):
                variables.append({'name': tok[:-1], 'type': 'character'})
                i += 1
                continue
            # plain name – peek at next token for $
            variables.append({'name': tok, 'type': 'numeric'})
            if i + 1 < len(tokens) and tokens[i + 1] == '$':
                variables[-1]['type'] = 'character'
                i += 2
                continue
            i += 1
        return variables

    def _parse_dataset_list(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse a SET or MERGE dataset list that may include options.
        Examples: 'sdtm.ae(in=a) dm(in=b keep=USUBJID RFSTDTC TRT01A)'
        Returns: [{'name': 'ae', 'full_name': 'sdtm.ae', 'libref': 'sdtm',
                   'in_var': 'a', 'keep': ['USUBJID', 'RFSTDTC', 'TRT01A']}]
        """
        results: List[Dict[str, Any]] = []
        # Paren-balanced tokeniser: respects spaces inside parentheses
        tokens = self._tokenise_balanced(text)
        for tok in tokens:
            m = re.match(r'([^(]+)(?:\(([^)]*)\))?', tok)
            if not m:
                continue
            raw_name = m.group(1).strip().rstrip(';')
            opts_str = m.group(2) or ''
            if not raw_name:
                continue
            # libref.dataset split
            if '.' in raw_name:
                lib, ds = raw_name.split('.', 1)
            else:
                lib, ds = 'work', raw_name
            entry: Dict[str, Any] = {
                'name':      ds.lower(),
                'full_name': raw_name.lower(),
                'libref':    lib.lower(),
            }
            # parse in= option
            in_m = re.search(r'\bin\s*=\s*(\w+)', opts_str, re.I)
            if in_m:
                entry['in_var'] = in_m.group(1).lower()
            # parse keep= option
            keep_m = re.search(r'\bkeep\s*=\s*([^)]+)', opts_str, re.I)
            if keep_m:
                entry['keep'] = keep_m.group(1).split()
            results.append(entry)
        return results

    @staticmethod
    def _tokenise_balanced(text: str) -> List[str]:
        """
        Split a dataset-list string into tokens, treating the contents of
        parentheses as opaque (so spaces inside parens don't split tokens).

        'sdtm.ae(in=a) dm(keep=USUBJID RFSTDTC TRT01A)' →
        ['sdtm.ae(in=a)', 'dm(keep=USUBJID RFSTDTC TRT01A)']
        """
        tokens: List[str] = []
        buf: List[str] = []
        depth = 0
        for ch in text.replace('\n', ' ').replace('\t', ' '):
            if ch == '(':
                depth += 1
                buf.append(ch)
            elif ch == ')':
                depth -= 1
                buf.append(ch)
            elif ch == ' ' and depth == 0:
                tok = ''.join(buf).strip().rstrip(';')
                if tok:
                    tokens.append(tok)
                buf = []
            else:
                buf.append(ch)
        tok = ''.join(buf).strip().rstrip(';')
        if tok:
            tokens.append(tok)
        return tokens

    def _proc_opts(self, stmt: str) -> Dict[str, Any]:
        opts: Dict[str, Any] = {}
        lo = stmt.lower()
        for key in ('data', 'out'):
            tag = f'{key}='
            if tag in lo:
                idx = lo.index(tag) + len(tag)
                val = stmt[idx:].split()[0].rstrip(';').strip()
                # Normalise dataset name to lowercase to match data_step/set normalisation
                opts[key] = val.split('.')[-1].lower()
                opts[f'{key}_full'] = val.lower()
        # Common PROC PRINT style flags
        if re.search(r'\bnoobs\b', lo):
            opts['noobs'] = True
        return opts

    def _stat_opts(self, stmt: str) -> List[str]:
        # Order matches SAS PROC MEANS default output: N Mean StdDev Min Max
        known = ['n', 'mean', 'std', 'min', 'max', 'median', 'var',
                 'sum', 'q1', 'q3', 'nmiss', 'stderr', 'cv', 'mode', 'range']
        lo = stmt.lower()
        found = [k for k in known if re.search(r'\b' + k + r'\b', lo)]
        # Default: N Mean Median StdDev Min Max Sum
        return found or ['n', 'mean', 'median', 'std', 'min', 'max', 'sum']

    def _parse_if(self, stmt: str) -> Dict[str, Any]:
        lo = stmt.lower()
        if 'then' not in lo:
            return {'type': 'if_statement', 'condition': stmt[3:].strip(),
                    'then_clause': None, 'else_clause': None}
        ti = lo.index('then')
        condition = stmt[3:ti].strip()
        rest = stmt[ti + 4:].strip()
        if 'else' in rest.lower():
            ei = rest.lower().index('else')
            then_part = rest[:ei].strip()
            else_part = rest[ei + 4:].strip()
        else:
            then_part = rest
            else_part = None
        return {
            'type': 'if_statement',
            'condition': condition,
            'then_clause': then_part,
            'else_clause': else_part,
        }

    def _parse_else_if(self, stmt: str) -> Dict[str, Any]:
        body = stmt[8:].strip()  # after "else if "
        lo = body.lower()
        if 'then' in lo:
            ti = lo.index('then')
            cond = body[:ti].strip()
            clause = body[ti + 4:].strip()
            return {'type': 'else_if_statement', 'condition': cond, 'then_clause': clause}
        return {'type': 'else_if_statement', 'condition': body, 'then_clause': None}

    def _parse_else(self, stmt: str) -> Dict[str, Any]:
        return {'type': 'else_statement', 'clause': stmt[5:].strip()}

    def _expand_var_list(self, text: str) -> List[str]:
        """
        Expand SAS variable list notation into individual names.
        Examples:
          "x1-x5"         → ["x1", "x2", "x3", "x4", "x5"]
          "flag1 flag2"    → ["flag1", "flag2"]
          "v1-v3 extra"   → ["v1", "v2", "v3", "extra"]
        """
        variables: List[str] = []
        for token in text.split():
            # SAS range: prefix + digits – prefix + digits  (e.g. x1-x5, var01-var10)
            m_range = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)(\d+)-[A-Za-z_][A-Za-z0-9_]*(\d+)$', token)
            if m_range:
                prefix = re.sub(r'\d+$', '', m_range.group(0).split('-')[0])
                try:
                    start = int(m_range.group(2))
                    end_tok = token.split('-')[1]
                    end = int(re.search(r'(\d+)$', end_tok).group(1))  # type: ignore[union-attr]
                    for i in range(start, end + 1):
                        variables.append(f"{prefix}{i}")
                except (ValueError, AttributeError):
                    variables.append(token)
            else:
                variables.append(token)
        return variables
