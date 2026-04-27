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

        # DATA step  (but NOT 'datalines')
        if lo.startswith('data ') and not lo.startswith('datalines'):
            parts = stmt.split()
            raw = parts[1] if len(parts) > 1 else 'work'
            lib, name = ('work', raw) if '.' not in raw else raw.split('.', 1)
            # Normalise to lowercase so simulator/generator lookups are case-insensitive
            return {'type': 'data_step', 'dataset': name.lower(), 'library': lib.lower()}

        # SET
        if lo.startswith('set '):
            rest = stmt[4:].strip()
            names = [tok.split('.')[-1].lower() for tok in rest.split() if tok]
            if not names:
                names = ['unknown']
            return {'type': 'set', 'datasets': names, 'dataset': names[0]}

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
        # Default matches SAS PROC MEANS default output: N Mean StdDev Min Max
        return found or ['n', 'mean', 'std', 'min', 'max']

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
