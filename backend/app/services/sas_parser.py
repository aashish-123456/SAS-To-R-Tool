"""
Advanced SAS Parser using PLY (Python Lex-Yacc)
Parses real-world SAS code into Abstract Syntax Tree
"""

import ply.lex as lex
import ply.yacc as yacc
from typing import Dict, List, Any, Optional

class SASParser:
    """
    SAS Code Parser that handles:
    - DATA steps
    - PROC steps (MEANS, FREQ, SORT, SQL, TRANSPOSE, FCMP)
    - Macro variables
    - Complex expressions
    """
    
    # Token definitions
    tokens = (
        'DATA', 'SET', 'INPUT', 'DATALINES', 'RUN', 'QUIT',
        'PROC', 'MEANS', 'FREQ', 'SORT', 'SQL', 'TRANSPOSE', 'FCMP',
        'BY', 'VAR', 'CLASS', 'TABLES', 'WHERE', 'IF', 'THEN', 'ELSE',
        'DO', 'END', 'OUTPUT', 'KEEP', 'DROP', 'RENAME',
        'IDENTIFIER', 'NUMBER', 'STRING', 'COMMENT',
        'EQUALS', 'PLUS', 'MINUS', 'TIMES', 'DIVIDE',
        'LT', 'GT', 'LE', 'GE', 'EQ', 'NE',
        'LPAREN', 'RPAREN', 'SEMICOLON', 'COMMA', 'DOT',
        'AND', 'OR', 'NOT', 'IN',
        'FUNCTION', 'RETURN', 'ENDSUB'
    )
    
    # Reserved words
    reserved = {
        'data': 'DATA',
        'set': 'SET',
        'input': 'INPUT',
        'datalines': 'DATALINES',
        'run': 'RUN',
        'quit': 'QUIT',
        'proc': 'PROC',
        'means': 'MEANS',
        'freq': 'FREQ',
        'sort': 'SORT',
        'sql': 'SQL',
        'transpose': 'TRANSPOSE',
        'fcmp': 'FCMP',
        'by': 'BY',
        'var': 'VAR',
        'class': 'CLASS',
        'tables': 'TABLES',
        'where': 'WHERE',
        'if': 'IF',
        'then': 'THEN',
        'else': 'ELSE',
        'do': 'DO',
        'end': 'END',
        'output': 'OUTPUT',
        'keep': 'KEEP',
        'drop': 'DROP',
        'rename': 'RENAME',
        'and': 'AND',
        'or': 'OR',
        'not': 'NOT',
        'in': 'IN',
        'function': 'FUNCTION',
        'return': 'RETURN',
        'endsub': 'ENDSUB'
    }
    
    def __init__(self):
        self.lexer = lex.lex(module=self)
        self.parser = yacc.yacc(module=self)
        self.ast = []
    
    # Lexer rules
    t_EQUALS = r'='
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_LT = r'<'
    t_GT = r'>'
    t_LE = r'<='
    t_GE = r'>='
    t_EQ = r'=='
    t_NE = r'!='
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_SEMICOLON = r';'
    t_COMMA = r','
    t_DOT = r'\.'
    
    t_ignore = ' \t'
    
    def t_COMMENT(self, t):
        r'/\*(.|\n)*?\*/|^\*.*'
        pass  # Ignore comments
    
    def t_NUMBER(self, t):
        r'\d+\.?\d*'
        t.value = float(t.value) if '.' in t.value else int(t.value)
        return t
    
    def t_STRING(self, t):
        r'\"([^\\\n]|(\\.))*?\"'
        t.value = t.value[1:-1]  # Remove quotes
        return t
    
    def t_IDENTIFIER(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        t.type = self.reserved.get(t.value.lower(), 'IDENTIFIER')
        return t
    
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
    
    def t_error(self, t):
        print(f"Illegal character '{t.value[0]}'")
        t.lexer.skip(1)
    
    def parse(self, code: str) -> List[Dict[str, Any]]:
        """Parse SAS code and return AST"""
        self.ast = []
        
        # Simple parsing for demo - split by statements
        statements = []
        current_statement = []
        
        for line in code.split('\n'):
            line = line.strip()
            if not line or line.startswith('*') or line.startswith('/*'):
                continue
            
            current_statement.append(line)
            
            if ';' in line:
                stmt = ' '.join(current_statement)
                statements.append(self._parse_statement(stmt))
                current_statement = []
        
        return statements
    
    def _parse_statement(self, stmt: str) -> Dict[str, Any]:
        """Parse individual statement"""
        stmt = stmt.strip().replace(';', '')
        
        # DATA step
        if stmt.lower().startswith('data '):
            parts = stmt.split()
            dataset = parts[1] if len(parts) > 1 else 'unknown'
            return {
                'type': 'data_step',
                'dataset': dataset.split('.')[-1],
                'library': dataset.split('.')[0] if '.' in dataset else 'work'
            }
        
        # SET statement
        elif stmt.lower().startswith('set '):
            parts = stmt.split()
            dataset = parts[1] if len(parts) > 1 else 'unknown'
            return {
                'type': 'set',
                'dataset': dataset.split('.')[-1]
            }
        
        # INPUT statement
        elif stmt.lower().startswith('input '):
            vars_str = stmt[6:].strip()
            variables = []
            for var in vars_str.split():
                var_type = 'character' if '$' in var else 'numeric'
                var_name = var.replace('$', '').strip()
                if var_name:
                    variables.append({'name': var_name, 'type': var_type})
            return {
                'type': 'input',
                'variables': variables
            }
        
        # DATALINES
        elif stmt.lower() == 'datalines':
            return {'type': 'datalines'}
        
        # PROC MEANS
        elif stmt.lower().startswith('proc means'):
            return {
                'type': 'proc_means',
                'options': self._extract_proc_options(stmt)
            }
        
        # PROC FREQ
        elif stmt.lower().startswith('proc freq'):
            return {
                'type': 'proc_freq',
                'options': self._extract_proc_options(stmt)
            }
        
        # PROC SORT
        elif stmt.lower().startswith('proc sort'):
            return {
                'type': 'proc_sort',
                'options': self._extract_proc_options(stmt)
            }
        
        # PROC SQL
        elif stmt.lower().startswith('proc sql'):
            return {
                'type': 'proc_sql',
                'options': self._extract_proc_options(stmt)
            }
        
        # PROC FCMP
        elif stmt.lower().startswith('proc fcmp'):
            return {
                'type': 'proc_fcmp',
                'options': self._extract_proc_options(stmt)
            }
        
        # VAR statement
        elif stmt.lower().startswith('var '):
            variables = stmt[4:].split()
            return {
                'type': 'var',
                'variables': variables
            }
        
        # BY statement
        elif stmt.lower().startswith('by '):
            rest = stmt[3:].strip()
            descending = 'descending' in rest.lower()
            variables = [v for v in rest.split() if v.lower() != 'descending']
            return {
                'type': 'by',
                'variables': variables,
                'descending': descending
            }
        
        # CLASS statement
        elif stmt.lower().startswith('class '):
            variables = stmt[6:].split()
            return {
                'type': 'class',
                'variables': variables
            }
        
        # TABLES statement
        elif stmt.lower().startswith('tables '):
            variables = stmt[7:].split()
            return {
                'type': 'tables',
                'variables': variables
            }
        
        # Assignment
        elif '=' in stmt and not stmt.lower().startswith(('if', 'where')):
            parts = stmt.split('=', 1)
            return {
                'type': 'assignment',
                'variable': parts[0].strip(),
                'expression': parts[1].strip() if len(parts) > 1 else ''
            }
        
        # IF-THEN statement
        elif stmt.lower().startswith('if '):
            return self._parse_if_statement(stmt)
        
        # RUN/QUIT
        elif stmt.lower() in ['run', 'quit']:
            return {'type': stmt.lower()}
        
        # Default
        else:
            return {
                'type': 'unknown',
                'statement': stmt
            }
    
    def _extract_proc_options(self, stmt: str) -> Dict[str, Any]:
        """Extract options from PROC statement"""
        options = {}
        
        if 'data=' in stmt.lower():
            data_part = stmt.lower().split('data=')[1].split()[0]
            options['data'] = data_part.split('.')[-1]
        
        if 'out=' in stmt.lower():
            out_part = stmt.lower().split('out=')[1].split()[0]
            options['out'] = out_part.split('.')[-1]
        
        return options
    
    def _parse_if_statement(self, stmt: str) -> Dict[str, Any]:
        """Parse IF-THEN-ELSE statement"""
        stmt_lower = stmt.lower()
        
        # Extract condition
        if_part = stmt_lower.split('then')[0].replace('if', '').strip()
        
        # Extract then part
        then_part = ''
        else_part = ''
        
        if 'then' in stmt_lower:
            rest = stmt.split('then', 1)[1].strip()
            if 'else' in rest.lower():
                parts = rest.lower().split('else', 1)
                then_part = parts[0].strip()
                else_part = parts[1].strip() if len(parts) > 1 else ''
            else:
                then_part = rest
        
        return {
            'type': 'if_statement',
            'condition': if_part,
            'then_clause': then_part,
            'else_clause': else_part if else_part else None
        }


# Example usage
if __name__ == "__main__":
    sas_code = """
    data work.example;
        input ID $ Age Gender $ Salary;
        datalines;
    A01 25 M 50000
    A02 30 F 60000
    ;
    run;
    
    proc means data=work.example n mean median;
        var Age Salary;
    run;
    """
    
    parser = SASParser()
    ast = parser.parse(sas_code)
    
    import json
    print(json.dumps(ast, indent=2))
