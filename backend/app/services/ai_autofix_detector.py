from enum import Enum
from dataclasses import dataclass, field
from typing import List

class IssueType(Enum):
    SEMICOLON = "semicolon"
    SYNTAX = "syntax"
    COMPATIBILITY = "compatibility"
    WARNING = "warning"

@dataclass
class Tier1Fix:
    line_number: int
    issue_type: IssueType
    message: str
    code_snippet: str
    fix_code: str
    confidence: float
    explanation: str

@dataclass
class Tier2Suggestion:
    line_number: int
    issue_type: IssueType
    message: str
    code_snippet: str
    fix_code: str
    confidence: float
    explanation: str
    requires_consent: bool

@dataclass
class Tier3Issue:
    line_number: int
    issue_type: IssueType
    message: str
    code_snippet: str
    explanation: str
    warning: bool

@dataclass
class AutoFixResult:
    tier1_fixes: List[Tier1Fix]
    tier2_suggestions: List[Tier2Suggestion]
    tier3_issues: List[Tier3Issue]
    can_proceed: bool

class AIAutoFixDetector:
    """
    AI Auto-Fix Detector. Scans code for common SAS formatting mistakes or incompatible logic
    and suggests auto-fixes (semicolons, spacing issues).
    """
    def analyze_code(self, code: str) -> AutoFixResult:
        # Standard auto-fixes
        tier1 = []
        tier2 = []
        tier3 = []
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            line_no = i + 1
            # Check for missing semicolon at end of statement (e.g. data step, run)
            stripped = line.strip()
            if stripped.upper() in ["RUN", "QUIT", "DATA", "PROC SORT"] and not stripped.endswith(';'):
                tier1.append(Tier1Fix(
                    line_number=line_no,
                    issue_type=IssueType.SEMICOLON,
                    message=f"Missing semicolon after '{stripped}' statement.",
                    code_snippet=line,
                    fix_code=line + ";",
                    confidence=0.99,
                    explanation="SAS compiler requires statements to terminate with semicolons."
                ))
            
            # Check for non-standard comment styles
            if stripped.startswith('//'):
                tier1.append(Tier1Fix(
                    line_number=line_no,
                    issue_type=IssueType.SYNTAX,
                    message="C-style comment '//' detected. Converting to SAS comment.",
                    code_snippet=line,
                    fix_code="* " + stripped[2:] + ";",
                    confidence=0.95,
                    explanation="SAS comments should start with '*' and end with ';'."
                ))
                
        return AutoFixResult(
            tier1_fixes=tier1,
            tier2_suggestions=tier2,
            tier3_issues=tier3,
            can_proceed=True
        )

    def apply_tier1_fixes(self, sas_code: str, fixes: List[Tier1Fix]) -> str:
        lines = sas_code.split('\n')
        for fix in fixes:
            idx = fix.line_number - 1
            if idx < len(lines):
                # Apply replacement
                lines[idx] = fix.fix_code
        return '\n'.join(lines)
