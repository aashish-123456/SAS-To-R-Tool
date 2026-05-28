import React, { useCallback, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Upload, File, X, CheckCircle2, AlertTriangle, AlertCircle,
  ChevronDown, ChevronRight, Wrench, ShieldAlert, ArrowRight,
  Cpu, ClipboardList, Zap, Info,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────

type ComplexityLevelNum = 1 | 2 | 3 | 4 | 5;

interface ComplexityInfo {
  level: ComplexityLevelNum;
  label: string;
  description: string;
  badge: string;  // tailwind color classes
  score: number;
}

interface ValidationIssue {
  type: 'syntax' | 'semantic';
  severity: 'error' | 'warning' | 'info';
  autoFixable: boolean;
  code: string;
  line?: number;
  message: string;
  reason: string;
  recommendation: string;
}

interface AutoFix {
  code: string;
  description: string;
  count: number;
}

interface ValidationReport {
  complexity: ComplexityInfo;
  constructs: string[];
  procCategories: string[];
  macroUsage: boolean;
  clinicalDomainIndicators: string[];
  sdtmAdamIndicators: string[];
  syntaxRiskLevel: 'low' | 'medium' | 'high';
  autoFixes: AutoFix[];
  manualIssues: ValidationIssue[];
  warnings: ValidationIssue[];
  overallStatus: 'ready' | 'auto_fixed' | 'manual_review_required';
  linesOfCode: number;
  nonBlankLines: number;
  fixedCode: string;
}

// ─────────────────────────────────────────────────────────────
// VALIDATION ENGINE
// ─────────────────────────────────────────────────────────────

function classifyComplexity(code: string): { complexity: ComplexityInfo; constructs: string[]; procCategories: string[]; clinicalIndicators: string[]; sdtmAdamIndicators: string[] } {
  const u = code.toUpperCase();
  let score = 0;
  const constructs: string[] = [];
  const procCategories: string[] = [];
  const clinicalIndicators: string[] = [];
  const sdtmAdamIndicators: string[] = [];

  // ── Level 1 – Basic ──────────────────────────────────────
  if (/\bDATA\s+\w+/.test(u)) { score += 1; constructs.push('DATA Step'); }
  if (/\bSET\s+\w+/.test(u)) { score += 1; constructs.push('SET'); }
  if (/\bPROC\s+MEANS\b/.test(u)) { score += 1; constructs.push('PROC MEANS'); procCategories.push('PROC MEANS'); }
  if (/\bPROC\s+FREQ\b/.test(u)) { score += 1; constructs.push('PROC FREQ'); procCategories.push('PROC FREQ'); }
  if (/\bPROC\s+SORT\b/.test(u)) { score += 1; constructs.push('PROC SORT'); procCategories.push('PROC SORT'); }
  if (/\bPROC\s+PRINT\b/.test(u)) { score += 1; constructs.push('PROC PRINT'); procCategories.push('PROC PRINT'); }
  if (/\bIF\s+.+THEN\b/.test(u)) { score += 1; constructs.push('IF-THEN Logic'); }
  if (/\bKEEP\b/.test(u)) { score += 1; constructs.push('KEEP'); }
  if (/\bDROP\b/.test(u)) { score += 1; constructs.push('DROP'); }
  if (/\bINPUT\b/.test(u) && /\bDATALINES\b|\bCARDS\b/.test(u)) { score += 1; constructs.push('DATALINES'); }

  // ── Level 2 – Intermediate ───────────────────────────────
  if (/\bPROC\s+SQL\b/.test(u)) { score += 4; constructs.push('PROC SQL'); procCategories.push('PROC SQL'); }
  if (/\bMERGE\s+\w+/.test(u)) { score += 3; constructs.push('MERGE'); }
  if (/\bFORMAT\b/.test(u)) { score += 1; constructs.push('FORMAT'); }
  if (/\bLABEL\b/.test(u)) { score += 1; constructs.push('LABEL'); }
  if (/\bLENGTH\b/.test(u)) { score += 1; constructs.push('LENGTH'); }
  if (/\bOUTPUT\b/.test(u)) { score += 1; constructs.push('OUTPUT'); }
  if (/\bRENAME\b/.test(u)) { score += 1; constructs.push('RENAME'); }
  if (/\bIN=\w+/.test(u)) { score += 2; constructs.push('Dataset IN= Option'); }

  // ── Level 3 – Advanced ───────────────────────────────────
  if (/%MACRO\b/i.test(code)) { score += 6; constructs.push('Macro Definition (%MACRO)'); }
  if (/&[A-Za-z_]\w*/.test(code)) { score += 3; constructs.push('Macro Variables'); }
  if (/\bARRAY\b/.test(u)) { score += 4; constructs.push('ARRAY'); }
  if (/\bRETAIN\b/.test(u)) { score += 3; constructs.push('RETAIN'); }
  if (/\bPROC\s+TRANSPOSE\b/.test(u)) { score += 3; constructs.push('PROC TRANSPOSE'); procCategories.push('PROC TRANSPOSE'); }
  if (/\bFIRST\.\w+/.test(u) || /\bLAST\.\w+/.test(u)) { score += 3; constructs.push('BY-Group Processing (FIRST/LAST)'); }
  if (/\bDO\s+[A-Z_]\w*\s*=/.test(u)) { score += 2; constructs.push('DO Loop'); }
  if (/\bSELECT\s*\(/.test(u) && /\bWHEN\s*\(/.test(u)) { score += 2; constructs.push('SELECT-WHEN'); }
  if (/\bPROC\s+REG\b/.test(u)) { score += 3; constructs.push('PROC REG'); procCategories.push('PROC REG'); }
  if (/\bPROC\s+UNIVARIATE\b/.test(u)) { score += 3; constructs.push('PROC UNIVARIATE'); procCategories.push('PROC UNIVARIATE'); }

  // ── Level 4 – Contextual Clinical ───────────────────────
  const sdtmVarPatterns = ['USUBJID', 'SUBJID', 'VISIT\\b', 'VISITNUM', 'AVISITN', 'PARAMCD', 'DOMAIN'];
  const sdtmFound = sdtmVarPatterns.filter(p => new RegExp(`\\b${p}`).test(u));
  if (sdtmFound.length > 0) {
    score += 6;
    sdtmAdamIndicators.push('SDTM Variables: ' + sdtmFound.slice(0, 3).join(', '));
    constructs.push('SDTM Variables');
  }
  const adamVarPatterns = ['\\bAVAL\\b', '\\bBASE\\b', '\\bCHG\\b', '\\bDTYPE\\b', '\\bANL01FL\\b', '\\bBASEFL\\b'];
  const adamFound = adamVarPatterns.filter(p => new RegExp(p).test(u));
  if (adamFound.length > 0) {
    score += 6;
    sdtmAdamIndicators.push('ADaM Variables: AVAL, BASE, CHG');
    constructs.push('ADaM Variables');
  }
  const popFlags = ['SAFFL', 'ITTFL', 'PPROTFL', 'COMPLFL', 'RANDFL', 'ENRLFL'];
  const foundFlags = popFlags.filter(f => new RegExp(`\\b${f}\\b`).test(u));
  if (foundFlags.length > 0) {
    score += 5;
    clinicalIndicators.push('Population Flags: ' + foundFlags.join(', '));
    constructs.push('Clinical Population Flags');
  }
  const adamDs = ['\\bADSL\\b', '\\bADAE\\b', '\\bADLB\\b', '\\bADTTE\\b', '\\bADRS\\b', '\\bADVS\\b'];
  const foundAdam = adamDs.filter(p => new RegExp(p).test(u));
  if (foundAdam.length > 0) {
    score += 7;
    clinicalIndicators.push('ADaM Datasets: ' + foundAdam.map(p => p.replace(/\\b/g, '')).join(', '));
    constructs.push('ADaM Analysis Datasets');
  }
  if (/\bODS\s+OUTPUT\b|\bODS\s+HTML\b|\bODS\s+PDF\b/.test(u)) { score += 3; constructs.push('ODS Output'); clinicalIndicators.push('ODS System'); }
  if (/\bPROC\s+REPORT\b/.test(u)) { score += 4; constructs.push('PROC REPORT'); procCategories.push('PROC REPORT'); clinicalIndicators.push('PROC REPORT'); }
  if (/\bPROC\s+TABULATE\b/.test(u)) { score += 4; constructs.push('PROC TABULATE'); procCategories.push('PROC TABULATE'); }
  if (/\bCDISC\b|\bSDTM\b|\bADAM\b/.test(u)) { score += 5; clinicalIndicators.push('CDISC Standards Reference'); }
  if (/\bYRDIF\b|\bINTCK\b|\bINTNX\b/.test(u)) { score += 3; clinicalIndicators.push('Clinical Date Functions'); }
  if (/\bIS8601DT\b|\bDATE9\b/.test(u)) { score += 2; clinicalIndicators.push('ISO8601/DATE9 Format'); }

  // ── Level 5 – Highly Contextual ─────────────────────────
  if (/\bPROC\s+MIXED\b/.test(u)) { score += 12; constructs.push('PROC MIXED (MMRM)'); procCategories.push('PROC MIXED'); clinicalIndicators.push('Linear Mixed Effects Model'); }
  if (/\bPROC\s+PHREG\b/.test(u)) { score += 12; constructs.push('PROC PHREG (Cox PH)'); procCategories.push('PROC PHREG'); clinicalIndicators.push('Cox Proportional Hazards'); }
  if (/\bPROC\s+LIFETEST\b/.test(u)) { score += 10; constructs.push('PROC LIFETEST (KM)'); procCategories.push('PROC LIFETEST'); clinicalIndicators.push('Kaplan-Meier Survival'); }
  if (/\bPROC\s+LOGISTIC\b/.test(u)) { score += 9; constructs.push('PROC LOGISTIC'); procCategories.push('PROC LOGISTIC'); clinicalIndicators.push('Logistic Regression'); }
  if (/\bPROC\s+GENMOD\b/.test(u)) { score += 9; constructs.push('PROC GENMOD'); procCategories.push('PROC GENMOD'); }
  if (/\bLSMEANS\b/.test(u)) { score += 5; constructs.push('LSMEANS'); clinicalIndicators.push('Least Squares Means'); }
  if (/\bREPEATED\b/.test(u) && /\bSUBJECT\s*=/.test(u)) { score += 6; constructs.push('Repeated Measures Structure'); clinicalIndicators.push('Repeated Measures (MMRM)'); }
  if (/\bHAZARDRATIO\b/.test(u)) { score += 5; constructs.push('HAZARDRATIO'); clinicalIndicators.push('Hazard Ratio Estimation'); }
  if (/\bESTIMATE\b/.test(u) && /\bCL\b/.test(u)) { score += 4; constructs.push('Contrast ESTIMATE'); }
  if (/\bDDFM\s*=\s*KR\b/.test(u)) { score += 5; clinicalIndicators.push('Kenward-Roger df (MMRM)'); }
  if (/\bBASELINE\s+OUT\s*=/.test(u)) { score += 4; constructs.push('BASELINE Statement'); clinicalIndicators.push('Survival Baseline'); }
  if (/\bPROC\s+STDRATE\b/.test(u)) { score += 6; constructs.push('PROC STDRATE'); procCategories.push('PROC STDRATE'); }

  // ── Determine Level ──────────────────────────────────────
  let level: ComplexityLevelNum;
  let label: string;
  let description: string;
  let badge: string;

  if (score >= 30) {
    level = 5; label = 'Highly Contextual';
    description = 'Complex clinical statistical analysis with survival, mixed models, or ADaM-level programming';
    badge = 'bg-red-100 text-red-700 border-red-200';
  } else if (score >= 18) {
    level = 4; label = 'Contextual Clinical';
    description = 'Clinical domain-aware programming with SDTM/ADaM structures, population flags, and reporting';
    badge = 'bg-orange-100 text-orange-700 border-orange-200';
  } else if (score >= 9) {
    level = 3; label = 'Advanced';
    description = 'Advanced SAS with macros, arrays, RETAIN, complex BY-group logic, and regression procedures';
    badge = 'bg-purple-100 text-purple-700 border-purple-200';
  } else if (score >= 4) {
    level = 2; label = 'Intermediate';
    description = 'Moderate complexity with PROC SQL, dataset merging, formatting, and multi-step processing';
    badge = 'bg-blue-100 text-blue-700 border-blue-200';
  } else {
    level = 1; label = 'Basic';
    description = 'Foundational SAS: DATA steps, standard PROCs, simple conditional logic';
    badge = 'bg-emerald-100 text-emerald-700 border-emerald-200';
  }

  return {
    complexity: { level, label, description, badge, score },
    constructs: [...new Set(constructs)],
    procCategories: [...new Set(procCategories)],
    clinicalIndicators: [...new Set(clinicalIndicators)],
    sdtmAdamIndicators: [...new Set(sdtmAdamIndicators)],
  };
}

function runValidationEngine(code: string): Omit<ValidationReport, 'complexity' | 'constructs' | 'procCategories' | 'clinicalDomainIndicators' | 'sdtmAdamIndicators' | 'macroUsage' | 'linesOfCode' | 'nonBlankLines'> {
  const autoFixes: AutoFix[] = [];
  const manualIssues: ValidationIssue[] = [];
  const warnings: ValidationIssue[] = [];
  let fixedCode = code;

  // ── AUTO-FIXES (punctuation-level: safe, intent is unambiguous) ──────────

  // Fix 1: Double/triple semicolons
  const dblSemiCount = (fixedCode.match(/;;+/g) || []).length;
  if (dblSemiCount > 0) {
    fixedCode = fixedCode.replace(/;;+/g, ';');
    autoFixes.push({ code: 'DOUBLE_SEMICOLON', description: 'Replaced duplicate semicolons with single semicolon', count: dblSemiCount });
  }

  // Fix 2: Trailing whitespace on lines
  const trailCount = fixedCode.split('\n').filter(l => /\s+$/.test(l)).length;
  if (trailCount > 0) {
    fixedCode = fixedCode.replace(/[ \t]+$/gm, '');
    autoFixes.push({ code: 'TRAILING_WHITESPACE', description: 'Removed trailing whitespace from lines', count: trailCount });
  }

  // Fix 3: Multiple consecutive blank lines → max 2
  const multiBlank = (fixedCode.match(/\n{4,}/g) || []).length;
  if (multiBlank > 0) {
    fixedCode = fixedCode.replace(/\n{4,}/g, '\n\n\n');
    autoFixes.push({ code: 'EXCESS_BLANK_LINES', description: 'Normalized excessive blank lines', count: multiBlank });
  }

  // Fix 4: Missing newline after semicolon (same-line compressed statements)
  const noSpaceAfterSemi = (fixedCode.match(/;[A-Za-z]/g) || []).length;
  if (noSpaceAfterSemi > 0) {
    fixedCode = fixedCode.replace(/;([A-Za-z])/g, ';\n$1');
    autoFixes.push({ code: 'MISSING_NEWLINE_AFTER_SEMICOLON', description: 'Added newline after compressed statements', count: noSpaceAfterSemi });
  }

  // Fix 5: RUN missing semicolon — catches RUN at end of ANY line, not just alone on a line.
  // Negative lookahead (?!\s*;) skips lines that already have RUN; or RUN   ;
  // Lookahead (?=\r?\n|$) matches end-of-line without consuming the newline character.
  const runNoSemi = (fixedCode.match(/\bRUN\b(?!\s*;)[ \t]*(?=\r?\n|$)/gi) || []).length;
  if (runNoSemi > 0) {
    fixedCode = fixedCode.replace(/\b(RUN)\b(?!\s*;)[ \t]*(?=\r?\n|$)/gi, '$1;');
    autoFixes.push({ code: 'MISSING_SEMICOLON_RUN', description: 'Added missing semicolons to RUN statements', count: runNoSemi });
  }

  // Fix 6: QUIT missing semicolon — same end-of-line approach as Fix 5
  const quitNoSemi = (fixedCode.match(/\bQUIT\b(?!\s*;)[ \t]*(?=\r?\n|$)/gi) || []).length;
  if (quitNoSemi > 0) {
    fixedCode = fixedCode.replace(/\b(QUIT)\b(?!\s*;)[ \t]*(?=\r?\n|$)/gi, '$1;');
    autoFixes.push({ code: 'MISSING_SEMICOLON_QUIT', description: 'Added missing semicolons to QUIT statements', count: quitNoSemi });
  }

  // Fix 7: %MEND without semicolon (at end of line, with or without macro name)
  const mendNoSemi = (fixedCode.match(/(%MEND(?:\s+\w+)?)(?!\s*;)[ \t]*(?=\r?\n|$)/gi) || []).length;
  if (mendNoSemi > 0) {
    fixedCode = fixedCode.replace(/(%MEND(?:\s+\w+)?)(?!\s*;)[ \t]*(?=\r?\n|$)/gi, '$1;');
    autoFixes.push({ code: 'MISSING_SEMICOLON_MEND', description: 'Added missing semicolons to %MEND statements', count: mendNoSemi });
  }

  // Fix 8: %MACRO header missing semicolon — %MACRO name or %MACRO name(params) at end of line
  const macroNoSemi = (fixedCode.match(/(%MACRO\s+\w+(?:\s*\([^)]*\))?)(?!\s*;)[ \t]*(?=\r?\n|$)/gi) || []).length;
  if (macroNoSemi > 0) {
    fixedCode = fixedCode.replace(/(%MACRO\s+\w+(?:\s*\([^)]*\))?)(?!\s*;)[ \t]*(?=\r?\n|$)/gi, '$1;');
    autoFixes.push({ code: 'MISSING_SEMICOLON_MACRO', description: 'Added missing semicolons to %MACRO definition headers', count: macroNoSemi });
  }

  // ── SYNTAX VALIDATION (runs on fixedCode — after all punctuation fixes) ──

  // Check 1: DATA/PROC block RUN/QUIT balance (structural — truly missing terminator line)
  const dataStepMatches = (fixedCode.match(/\bDATA\s+\w/gi) || []).length;
  const procMatches = (fixedCode.match(/\bPROC\s+\w/gi) || []).length;
  const runMatches = (fixedCode.match(/\bRUN\s*;/gi) || []).length;
  const quitMatches = (fixedCode.match(/\bQUIT\s*;/gi) || []).length;
  const totalBlocks = dataStepMatches + procMatches;
  const totalTerminators = runMatches + quitMatches;
  if (totalBlocks > 0 && totalTerminators < totalBlocks - 1) {
    const missing = totalBlocks - totalTerminators;
    manualIssues.push({
      type: 'syntax', severity: 'error', autoFixable: false,
      code: 'MISSING_RUN_QUIT',
      message: `${missing} DATA/PROC block(s) are missing RUN; or QUIT; — add the terminator line`,
      reason: 'SAS requires each DATA step and PROC block to end with RUN; (or QUIT; for PROC SQL/IML). The missing statement cannot be inferred automatically.',
      recommendation: 'Add RUN; after each DATA step and PROC block. Use QUIT; for PROC SQL/IML.',
    });
  }

  // Check 2: DO/END balance (structural — missing an entire block boundary)
  const doOpen = (fixedCode.match(/\bDO\b(?!\s+OVER)/gi) || []).length;
  const doEnd = (fixedCode.match(/\bEND\s*;/gi) || []).length;
  if (Math.abs(doOpen - doEnd) > 1) {
    manualIssues.push({
      type: 'syntax', severity: 'error', autoFixable: false,
      code: 'DO_END_IMBALANCE',
      message: `DO/END imbalance: ${doOpen} DO block(s) found, ${doEnd} END; statement(s) — add or remove the missing block boundary`,
      reason: 'Unbalanced DO/END blocks cause SAS to misinterpret program structure. The correct location to insert or remove END; cannot be determined automatically.',
      recommendation: 'Match every DO or DO WHILE/UNTIL/i=1 TO N with a corresponding END;',
    });
  }

  // Check 3: %MACRO / %MEND count mismatch (structural — a whole macro definition or closure is missing)
  const macroOpen = (fixedCode.match(/%MACRO\b/gi) || []).length;
  const macroClose = (fixedCode.match(/%MEND\b/gi) || []).length;
  if (macroOpen !== macroClose) {
    manualIssues.push({
      type: 'syntax', severity: 'error', autoFixable: false,
      code: 'MACRO_BALANCE',
      message: `%MACRO/%MEND count mismatch: ${macroOpen} %MACRO definition(s), ${macroClose} %MEND closure(s) — a whole macro block is missing`,
      reason: 'Every %MACRO must have a matching %MEND. The correct scope boundary cannot be inferred automatically.',
      recommendation: 'Add %MEND <macro_name>; at the end of each unclosed macro definition',
    });
  }

  // Check 4: PROC SQL missing QUIT (structural — entire QUIT line is absent)
  const sqlBlocks = (fixedCode.match(/\bPROC\s+SQL\b/gi) || []).length;
  if (sqlBlocks > 0 && quitMatches < sqlBlocks) {
    manualIssues.push({
      type: 'syntax', severity: 'error', autoFixable: false,
      code: 'SQL_MISSING_QUIT',
      message: `${sqlBlocks} PROC SQL block(s) but only ${quitMatches} QUIT; — add QUIT; to close each SQL session`,
      reason: 'PROC SQL must end with QUIT;. RUN; does not close the SQL session. The correct position cannot be determined automatically.',
      recommendation: 'Add QUIT; at the end of each PROC SQL block',
    });
  }

  // Check 5: Parentheses balance (structural — missing open or close paren, position unknown)
  const openParens = (fixedCode.match(/\(/g) || []).length;
  const closeParens = (fixedCode.match(/\)/g) || []).length;
  if (Math.abs(openParens - closeParens) > 2) {
    manualIssues.push({
      type: 'syntax', severity: 'error', autoFixable: false,
      code: 'PAREN_IMBALANCE',
      message: `Parentheses imbalance: ${openParens} '(' vs ${closeParens} ')' — locate and add the missing parenthesis`,
      reason: 'Unbalanced parentheses cause syntax errors. The exact location of the missing paren cannot be determined automatically.',
      recommendation: 'Review function calls, WHERE clauses, and SQL expressions for missing parentheses',
    });
  }

  // Check 6: MERGE without BY (semantic — BY variable(s) are unknown, must be supplied by user)
  const mergeCount = (fixedCode.match(/\bMERGE\s+\w/gi) || []).length;
  const byCount = (fixedCode.match(/\bBY\s+\w/gi) || []).length;
  if (mergeCount > 0 && byCount === 0) {
    manualIssues.push({
      type: 'semantic', severity: 'error', autoFixable: false,
      code: 'MERGE_NO_BY',
      message: 'MERGE statement found without a BY clause — specify the merge key variable(s)',
      reason: 'MERGE without BY does an observation-number join, almost never the intent. The key variable(s) are domain knowledge — they cannot be inferred from the code.',
      recommendation: 'Add BY <key_variable(s)>; after the MERGE statement and ensure both datasets are sorted by that key',
    });
  }

  // ── SEMANTIC VALIDATION ───────────────────────────────────

  // Check 7: Unresolved macro variables
  const macroVarMatches = [...(fixedCode.match(/&[A-Za-z_][A-Za-z0-9_]*/g) || [])];
  const uniqueMacroVars = [...new Set(macroVarMatches)];
  if (uniqueMacroVars.length > 0) {
    const definedMacros = [...(fixedCode.match(/%LET\s+([A-Za-z_]\w*)\s*=/gi) || [])].map(m => {
      const match = m.match(/%LET\s+([A-Za-z_]\w*)/i);
      return match ? `&${match[1].toLowerCase()}` : '';
    }).filter(Boolean);
    const unresolved = uniqueMacroVars.filter(v => !definedMacros.includes(v.toLowerCase()));
    if (unresolved.length > 0) {
      warnings.push({
        type: 'semantic', severity: 'warning', autoFixable: false,
        code: 'UNRESOLVED_MACRO_VARS',
        message: `${unresolved.length} macro variable(s) may not be defined: ${unresolved.slice(0, 5).join(', ')}${unresolved.length > 5 ? '...' : ''}`,
        reason: 'Unresolved macro variables (&name) will be left as literal text during conversion, potentially breaking R translation logic.',
        recommendation: 'Define all macro variables with %LET before use, or expand them to literal values before upload',
      });
    }
  }

  // Check 8: Macro calls without definitions
  const macroCalls = [...(fixedCode.match(/%[A-Za-z_]\w*\s*\(/g) || [])].map(m => m.replace(/\s*\($/, '').toLowerCase());
  const macroDefsRaw = [...(fixedCode.match(/%MACRO\s+([A-Za-z_]\w*)/gi) || [])].map(m => {
    const match = m.match(/%MACRO\s+([A-Za-z_]\w*)/i);
    return match ? `%${match[1].toLowerCase()}` : '';
  }).filter(Boolean);
  const builtinMacros = ['%if', '%then', '%else', '%do', '%end', '%let', '%put', '%include', '%global', '%local', '%eval', '%sysevalf', '%sysfunc', '%qsysfunc', '%upcase', '%lowcase', '%substr', '%scan', '%trim', '%left', '%right', '%compress', '%index', '%nrquote', '%str', '%nrstr', '%bquote', '%nrbquote'];
  const unresolvedCalls = macroCalls.filter(c => !macroDefsRaw.includes(c) && !builtinMacros.includes(c));
  if (unresolvedCalls.length > 0) {
    const unique = [...new Set(unresolvedCalls)];
    warnings.push({
      type: 'semantic', severity: 'warning', autoFixable: false,
      code: 'UNDEFINED_MACRO_CALLS',
      message: `${unique.length} macro call(s) with no definition found: ${unique.slice(0, 4).join(', ')}${unique.length > 4 ? '...' : ''}`,
      reason: 'Calling an undefined macro will produce a WARNING in SAS and may silently skip logic during R conversion.',
      recommendation: 'Include macro definitions or provide a fully-expanded version of the program',
    });
  }

  // Check 9: BY-group without PROC SORT
  const hasFirstLast = /\bFIRST\.\w+|\bLAST\.\w+/.test(fixedCode.toUpperCase());
  const hasSort = /\bPROC\s+SORT\b/i.test(fixedCode);
  if (hasFirstLast && !hasSort) {
    warnings.push({
      type: 'semantic', severity: 'warning', autoFixable: false,
      code: 'BY_GROUP_NO_SORT',
      message: 'FIRST./LAST. BY-group variables used but no PROC SORT detected',
      reason: 'FIRST./LAST. variables require the dataset to be pre-sorted. Without prior sorting, BY-group logic produces incorrect results.',
      recommendation: 'Add PROC SORT DATA=<dataset>; BY <group_vars>; RUN; before the DATA step using FIRST./LAST.',
    });
  }

  // Check 10: RETAIN without explicit initialization
  const retainMatches = (fixedCode.match(/\bRETAIN\b/gi) || []).length;
  if (retainMatches > 1) {
    warnings.push({
      type: 'semantic', severity: 'info', autoFixable: false,
      code: 'RETAIN_USAGE',
      message: `${retainMatches} RETAIN statement(s) detected — verify initialization values`,
      reason: 'RETAIN carries variable values across observations. In R conversion, this requires explicit cumulative logic. Missing initialization may produce off-by-one errors.',
      recommendation: 'Ensure RETAIN initializes all variables with explicit starting values (e.g., RETAIN counter 0;)',
    });
  }

  // Check 11: Complex clinical procedure warnings
  if (/\bPROC\s+MIXED\b/i.test(fixedCode)) {
    warnings.push({
      type: 'semantic', severity: 'warning', autoFixable: false,
      code: 'PROC_MIXED_COMPLEXITY',
      message: 'PROC MIXED detected — requires nlme/lme4 R packages with manual parameter mapping',
      reason: 'PROC MIXED options (DDFM, REPEATED, LSMEANS, covariance TYPE=) have no direct R equivalent and require careful manual mapping to lme4::lmer() or nlme::lme().',
      recommendation: 'Review the generated R code for PROC MIXED carefully. The emmeans package handles LSMEANS; covariance structures require manual configuration.',
    });
  }
  if (/\bPROC\s+PHREG\b/i.test(fixedCode)) {
    warnings.push({
      type: 'semantic', severity: 'warning', autoFixable: false,
      code: 'PROC_PHREG_COMPLEXITY',
      message: 'PROC PHREG (Cox PH) detected — requires survival package in R',
      reason: 'Cox model syntax, HAZARDRATIO statements, and ASSESS PH require the survival package. BASELINE OUT= statement needs manual reconstruction.',
      recommendation: 'Verify survival::coxph() and survminer package integration in the generated R code',
    });
  }
  if (/\bPROC\s+LIFETEST\b/i.test(fixedCode)) {
    warnings.push({
      type: 'semantic', severity: 'warning', autoFixable: false,
      code: 'PROC_LIFETEST_COMPLEXITY',
      message: 'PROC LIFETEST (Kaplan-Meier) detected — requires survival/survminer packages',
      reason: 'Kaplan-Meier curves, log-rank tests, and ATRISK plots are rendered differently between SAS and R.',
      recommendation: 'Review survival::survfit() and ggsurvplot() for equivalence with PROC LIFETEST options',
    });
  }

  // ── Determine Overall Status ──────────────────────────────
  let overallStatus: ValidationReport['overallStatus'];
  if (manualIssues.length > 0) {
    overallStatus = 'manual_review_required';
  } else if (autoFixes.length > 0) {
    overallStatus = 'auto_fixed';
  } else {
    overallStatus = 'ready';
  }

  const syntaxErrors = manualIssues.filter(i => i.type === 'syntax' && i.severity === 'error').length;
  const syntaxRiskLevel = syntaxErrors > 0 ? 'high' : warnings.length > 2 ? 'medium' : 'low';

  return { autoFixes, manualIssues, warnings, overallStatus, syntaxRiskLevel, fixedCode };
}

function analyzeSAS(code: string): ValidationReport {
  const lines = code.split('\n');
  const nonBlankLines = lines.filter(l => l.trim().length > 0).length;
  const { complexity, constructs, procCategories, clinicalIndicators, sdtmAdamIndicators } = classifyComplexity(code);
  const macroUsage = /%MACRO\b/i.test(code) || /&[A-Za-z_]\w*/.test(code);
  const validationResult = runValidationEngine(code);
  return {
    complexity,
    constructs,
    procCategories,
    macroUsage,
    clinicalDomainIndicators: clinicalIndicators,
    sdtmAdamIndicators,
    linesOfCode: lines.length,
    nonBlankLines,
    ...validationResult,
  };
}

// ─────────────────────────────────────────────────────────────
// SMALL UI COMPONENTS
// ─────────────────────────────────────────────────────────────

const SeverityIcon: React.FC<{ severity: ValidationIssue['severity'] }> = ({ severity }) => {
  if (severity === 'error') return <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />;
  if (severity === 'warning') return <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />;
  return <Info className="w-4 h-4 text-blue-500 flex-shrink-0" />;
};

const SeverityBadge: React.FC<{ severity: ValidationIssue['severity'] }> = ({ severity }) => {
  const map = {
    error: 'bg-red-100 text-red-700',
    warning: 'bg-amber-100 text-amber-700',
    info: 'bg-blue-100 text-blue-700',
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide ${map[severity]}`}>
      {severity}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// MANUAL ISSUES MODAL
// ─────────────────────────────────────────────────────────────

const ManualIssuesModal: React.FC<{
  issues: ValidationIssue[];
  onDismiss: () => void;
}> = ({ issues, onDismiss }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-start gap-4 p-6 border-b border-red-100 bg-red-50/60">
        <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
          <ShieldAlert className="w-5 h-5 text-red-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-extrabold text-slate-900 leading-tight">Manual Review Required</h2>
          <p className="text-sm text-slate-600 mt-0.5">
            {issues.length} issue{issues.length !== 1 ? 's' : ''} detected that cannot be auto-corrected and may impact logic, execution flow, or clinical semantics.
          </p>
        </div>
        <button onClick={onDismiss} className="p-1.5 rounded-lg hover:bg-red-100 transition-colors text-slate-400 hover:text-red-600 flex-shrink-0">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Issues list */}
      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        {issues.map((issue, idx) => (
          <div key={idx} className={`rounded-xl border p-4 ${issue.severity === 'error' ? 'border-red-200 bg-red-50/40' : 'border-amber-200 bg-amber-50/40'}`}>
            <div className="flex items-start gap-3">
              <SeverityIcon severity={issue.severity} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <SeverityBadge severity={issue.severity} />
                  <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">{issue.code}</span>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase">{issue.type}</span>
                </div>
                <p className="text-sm font-semibold text-slate-800 leading-snug">{issue.message}</p>
                <div className="mt-2 space-y-1.5">
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Reason: </span>
                    <span className="text-xs text-slate-600">{issue.reason}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wide">Fix: </span>
                    <span className="text-xs text-slate-700 font-medium">{issue.recommendation}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-5 border-t border-slate-100 bg-slate-50">
        <p className="text-xs text-slate-500 mb-3 text-center leading-relaxed">
          Please correct the SAS code externally and re-upload the corrected file to proceed.
        </p>
        <button
          onClick={onDismiss}
          className="w-full flex items-center justify-center gap-2 py-2.5 bg-slate-800 hover:bg-slate-900 text-white text-sm font-bold rounded-xl transition-colors"
        >
          <X className="w-4 h-4" />
          Dismiss — Upload Corrected File
        </button>
      </div>
    </div>
  </div>
);

// ─────────────────────────────────────────────────────────────
// UPLOAD STEP
// ─────────────────────────────────────────────────────────────

type Phase = 'idle' | 'reading' | 'analyzing' | 'done' | 'blocked';

const hasAllowedDatasetExt = (name: string) => /\.(sas7bdat|xpt|csv)$/i.test(name);

const BASIC_SAS_HINTS = [/\bdata\s+\w+/i, /\bproc\s+\w+/i, /\brun\s*;/i, /\bset\s+\w+/i];
const isLikelySasCode = (text: string) => BASIC_SAS_HINTS.filter(rx => rx.test(text)).length >= 2;

const UploadStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [phase, setPhase] = useState<Phase>('idle');
  const [sasFile, setSasFile] = useState<File | null>(null);
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showAutoFixDetail, setShowAutoFixDetail] = useState(false);
  const [showWarningDetail, setShowWarningDetail] = useState(false);
  const [datasetFiles, setDatasetFiles] = useState<File[]>([]);
  const [datasetEnabled, setDatasetEnabled] = useState(false);
  const [datasetError, setDatasetError] = useState('');
  const [fileError, setFileError] = useState('');

  const resetFile = () => {
    setSasFile(null);
    setReport(null);
    setPhase('idle');
    setFileError('');
    setShowModal(false);
  };

  const onDropSas = useCallback(async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length) return;
    const candidate = acceptedFiles[0];
    if (!/\.(sas|txt)$/i.test(candidate.name)) {
      setFileError('Only .sas or .txt files are accepted for SAS code.');
      return;
    }
    setFileError('');
    setPhase('reading');
    setSasFile(candidate);

    let text: string;
    try {
      text = await candidate.text();
    } catch {
      setFileError('Could not read file. Please try again.');
      setPhase('idle');
      return;
    }

    if (!isLikelySasCode(text)) {
      setFileError('This file does not appear to contain SAS code. Please upload a valid .sas or .txt file containing SAS programs.');
      setSasFile(null);
      setPhase('idle');
      return;
    }

    setPhase('analyzing');
    // small delay for UX — makes the "analyzing" phase feel real
    await new Promise(r => setTimeout(r, 600));

    const result = analyzeSAS(text);
    setReport(result);

    if (result.overallStatus === 'manual_review_required') {
      setPhase('blocked');
      setShowModal(true);
    } else {
      setPhase('done');
    }
  }, []);

  const onDropDatasets = useCallback((acceptedFiles: File[]) => {
    const invalid = acceptedFiles.find(f => !hasAllowedDatasetExt(f.name) || f.size === 0);
    if (invalid) {
      setDatasetError('Invalid file. Upload non-empty .sas7bdat, .xpt, or .csv files only.');
      return;
    }
    setDatasetError('');
    setDatasetFiles(prev => [...prev, ...acceptedFiles.filter(f => !prev.find(p => p.name === f.name))]);
  }, []);

  const { getRootProps: getSasRootProps, getInputProps: getSasInputProps, isDragActive } = useDropzone({
    onDrop: onDropSas, accept: { 'text/plain': ['.sas', '.txt'] }, multiple: false,
  });

  const { getRootProps: getDsRootProps, getInputProps: getDsInputProps } = useDropzone({
    onDrop: onDropDatasets,
    accept: { 'application/octet-stream': ['.sas7bdat', '.xpt'], 'text/csv': ['.csv'] },
    multiple: true, disabled: !datasetEnabled,
  });

  const canContinue = phase === 'done' && !!sasFile && !datasetError;

  const handleContinue = () => {
    navigate(`/projects/${projectId}/preview-input`, {
      state: { sasFile, datasetFiles, datasetEnabled, validationReport: report },
    });
  };

  // ── Risk level chip helper ─────────────────────────────────
  const riskChip = (level: 'low' | 'medium' | 'high') => {
    const map = { low: 'bg-emerald-100 text-emerald-700', medium: 'bg-amber-100 text-amber-700', high: 'bg-red-100 text-red-700' };
    return <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${map[level]}`}>{level} risk</span>;
  };

  return (
    <>
      {showModal && report && (
        <ManualIssuesModal
          issues={report.manualIssues}
          onDismiss={() => { setShowModal(false); resetFile(); }}
        />
      )}

      <div className="space-y-5 max-w-4xl">

        {/* ── Step Header ── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
              <Upload className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-extrabold text-slate-900 leading-tight">SAS Intake & Validation</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Clinical SAS Intake Engine — file qualification, complexity classification, syntax + semantic validation, and controlled AutoFix.
              </p>
            </div>
          </div>
        </div>

        {/* ── SAS File Upload ── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <p className="text-sm font-bold text-slate-800">SAS Program File</p>
            <p className="text-xs text-slate-400 mt-0.5">.sas or .txt — executable SAS programs only</p>
          </div>
          <div className="p-6">

            {/* Drop Zone */}
            {phase === 'idle' && (
              <div
                {...getSasRootProps()}
                className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
                  isDragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-blue-400 hover:bg-slate-50'
                }`}
              >
                <input {...getSasInputProps()} />
                <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Upload className="w-7 h-7 text-slate-400" />
                </div>
                <p className="text-sm font-semibold text-slate-700 mb-1">Drop your SAS file here</p>
                <p className="text-xs text-slate-400 mb-4">or click to browse — .sas and .txt files accepted</p>
                <div className="flex flex-wrap gap-2 justify-center text-[11px] text-slate-400">
                  {['DATA Step', 'PROC MEANS/FREQ', 'PROC SQL', 'Macros', 'PROC MIXED', 'PROC PHREG'].map(t => (
                    <span key={t} className="bg-slate-100 px-2.5 py-1 rounded-full">{t}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Reading / Analyzing */}
            {(phase === 'reading' || phase === 'analyzing') && (
              <div className="flex flex-col items-center justify-center py-12 gap-4">
                <div className="w-12 h-12 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin" style={{ borderWidth: '3px' }} />
                <div className="text-center">
                  <p className="text-sm font-bold text-slate-800">
                    {phase === 'reading' ? 'Reading file…' : 'Running Validation Engine…'}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {phase === 'analyzing' ? 'Classifying complexity · Syntax check · Semantic analysis · AutoFix' : 'Loading SAS program…'}
                  </p>
                </div>
              </div>
            )}

            {/* File Error */}
            {fileError && phase === 'idle' && (
              <div className="mt-4 flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-red-700">File Rejected</p>
                  <p className="text-xs text-red-600 mt-0.5">{fileError}</p>
                </div>
              </div>
            )}

            {/* File accepted + report */}
            {(phase === 'done' || phase === 'blocked') && sasFile && report && (
              <div className="space-y-4">

                {/* File info bar */}
                <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                    <File className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-slate-900 truncate">{sasFile.name}</p>
                    <p className="text-xs text-slate-500">
                      {(sasFile.size / 1024).toFixed(1)} KB · {report.linesOfCode} total lines · {report.nonBlankLines} code lines
                    </p>
                  </div>
                  <button onClick={resetFile} className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Complexity + Constructs */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Complexity card */}
                  <div className="rounded-xl border border-slate-200 p-4 bg-white">
                    <div className="flex items-center gap-2 mb-2">
                      <Cpu className="w-4 h-4 text-slate-500" />
                      <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">Complexity</span>
                    </div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-extrabold border ${report.complexity.badge}`}>
                        Level {report.complexity.level} · {report.complexity.label}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">{report.complexity.description}</p>
                    <p className="text-[10px] text-slate-400 mt-1">Score: {report.complexity.score}</p>
                  </div>

                  {/* Metadata card */}
                  <div className="rounded-xl border border-slate-200 p-4 bg-white">
                    <div className="flex items-center gap-2 mb-2">
                      <ClipboardList className="w-4 h-4 text-slate-500" />
                      <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">Program Metadata</span>
                    </div>
                    <div className="space-y-1 text-xs text-slate-600">
                      <div className="flex justify-between">
                        <span>PROC Categories</span>
                        <span className="font-semibold">{report.procCategories.length > 0 ? report.procCategories.length + ' detected' : 'None'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Macro Usage</span>
                        <span className={`font-semibold ${report.macroUsage ? 'text-amber-600' : 'text-emerald-600'}`}>{report.macroUsage ? 'Yes' : 'No'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Clinical Indicators</span>
                        <span className="font-semibold">{report.clinicalDomainIndicators.length}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>SDTM/ADaM Refs</span>
                        <span className="font-semibold">{report.sdtmAdamIndicators.length}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Syntax Risk</span>
                        {riskChip(report.syntaxRiskLevel)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Detected Constructs */}
                {report.constructs.length > 0 && (
                  <div className="rounded-xl border border-slate-200 p-4 bg-white">
                    <p className="text-xs font-bold text-slate-600 uppercase tracking-wide mb-2.5">Detected SAS Constructs</p>
                    <div className="flex flex-wrap gap-1.5">
                      {report.constructs.map(c => (
                        <span key={c} className="text-[11px] bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-medium">{c}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Clinical Indicators */}
                {report.clinicalDomainIndicators.length > 0 && (
                  <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-4">
                    <p className="text-xs font-bold text-blue-700 uppercase tracking-wide mb-2">Clinical Domain Indicators</p>
                    <div className="flex flex-wrap gap-1.5">
                      {report.clinicalDomainIndicators.map(c => (
                        <span key={c} className="text-[11px] bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full font-medium">{c}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Validation Results */}
                <div className="rounded-xl border border-slate-200 overflow-hidden">
                  <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
                    <p className="text-xs font-bold text-slate-600 uppercase tracking-wide">Validation Results</p>
                  </div>
                  <div className="divide-y divide-slate-100">

                    {/* Syntax */}
                    <div className="flex items-center gap-3 px-4 py-3">
                      {report.manualIssues.filter(i => i.type === 'syntax').length === 0 ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                      )}
                      <span className="text-sm font-medium text-slate-700 flex-1">Syntax Validation</span>
                      {report.manualIssues.filter(i => i.type === 'syntax').length === 0 ? (
                        <span className="text-xs font-semibold text-emerald-600">Passed</span>
                      ) : (
                        <span className="text-xs font-semibold text-red-600">{report.manualIssues.filter(i => i.type === 'syntax').length} issue(s)</span>
                      )}
                    </div>

                    {/* Semantic */}
                    <div className="flex items-center gap-3 px-4 py-3">
                      {report.manualIssues.filter(i => i.type === 'semantic').length === 0 ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                      )}
                      <span className="text-sm font-medium text-slate-700 flex-1">Semantic Validation</span>
                      {report.manualIssues.filter(i => i.type === 'semantic').length === 0 ? (
                        <span className="text-xs font-semibold text-emerald-600">Passed</span>
                      ) : (
                        <span className="text-xs font-semibold text-red-600">{report.manualIssues.filter(i => i.type === 'semantic').length} issue(s)</span>
                      )}
                    </div>

                    {/* AutoFix */}
                    {report.autoFixes.length > 0 && (
                      <div>
                        <button
                          onClick={() => setShowAutoFixDetail(prev => !prev)}
                          className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                        >
                          <Wrench className="w-4 h-4 text-blue-500 flex-shrink-0" />
                          <span className="text-sm font-medium text-slate-700 flex-1">AutoFix Applied</span>
                          <span className="text-xs font-semibold text-blue-600">{report.autoFixes.length} fix(es)</span>
                          {showAutoFixDetail ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                        </button>
                        {showAutoFixDetail && (
                          <div className="px-4 pb-3 space-y-1.5">
                            {report.autoFixes.map(fix => (
                              <div key={fix.code} className="flex items-start gap-2 text-xs text-slate-600 bg-blue-50 rounded-lg p-2.5">
                                <Zap className="w-3 h-3 text-blue-500 mt-0.5 flex-shrink-0" />
                                <span>{fix.description} <span className="text-slate-400">({fix.count}×)</span></span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Warnings */}
                    {report.warnings.length > 0 && (
                      <div>
                        <button
                          onClick={() => setShowWarningDetail(prev => !prev)}
                          className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                        >
                          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                          <span className="text-sm font-medium text-slate-700 flex-1">Warnings / Informational</span>
                          <span className="text-xs font-semibold text-amber-600">{report.warnings.length} notice(s)</span>
                          {showWarningDetail ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                        </button>
                        {showWarningDetail && (
                          <div className="px-4 pb-3 space-y-2">
                            {report.warnings.map((w, i) => (
                              <div key={i} className={`rounded-lg p-3 text-xs space-y-1 ${w.severity === 'warning' ? 'bg-amber-50 border border-amber-100' : 'bg-blue-50 border border-blue-100'}`}>
                                <div className="flex items-center gap-2">
                                  <SeverityBadge severity={w.severity} />
                                  <span className="font-mono text-[10px] text-slate-400">{w.code}</span>
                                </div>
                                <p className="font-semibold text-slate-700">{w.message}</p>
                                <p className="text-slate-500">{w.recommendation}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Conversion Readiness Report */}
                <div className={`rounded-xl border p-5 ${
                  report.overallStatus === 'manual_review_required'
                    ? 'border-red-200 bg-red-50/60'
                    : report.overallStatus === 'auto_fixed'
                    ? 'border-blue-200 bg-blue-50/50'
                    : 'border-emerald-200 bg-emerald-50/50'
                }`}>
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      report.overallStatus === 'manual_review_required' ? 'bg-red-100' :
                      report.overallStatus === 'auto_fixed' ? 'bg-blue-100' : 'bg-emerald-100'
                    }`}>
                      {report.overallStatus === 'manual_review_required' ? (
                        <ShieldAlert className="w-5 h-5 text-red-600" />
                      ) : report.overallStatus === 'auto_fixed' ? (
                        <Wrench className="w-5 h-5 text-blue-600" />
                      ) : (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm font-extrabold tracking-tight ${
                        report.overallStatus === 'manual_review_required' ? 'text-red-700' :
                        report.overallStatus === 'auto_fixed' ? 'text-blue-700' : 'text-emerald-700'
                      }`}>
                        {report.overallStatus === 'manual_review_required'
                          ? 'MANUAL REVIEW REQUIRED — Cannot Proceed'
                          : report.overallStatus === 'auto_fixed'
                          ? 'READY — AutoFix Applied Successfully'
                          : 'READY FOR CONVERSION'}
                      </p>
                      <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                        {report.overallStatus === 'manual_review_required'
                          ? `${report.manualIssues.length} blocking issue(s) must be resolved externally. Correct and re-upload.`
                          : report.overallStatus === 'auto_fixed'
                          ? `${report.autoFixes.length} safe formatting fix(es) applied · ${report.warnings.length} informational notice(s) · Complexity: ${report.complexity.label}`
                          : `Validation complete · Complexity: ${report.complexity.label} · ${report.warnings.length > 0 ? report.warnings.length + ' notice(s)' : 'No issues'}`
                        }
                      </p>
                    </div>
                    {report.overallStatus === 'manual_review_required' && (
                      <button
                        onClick={() => setShowModal(true)}
                        className="flex-shrink-0 text-xs font-semibold text-red-600 hover:text-red-700 underline"
                      >
                        View Issues
                      </button>
                    )}
                  </div>
                </div>

              </div>
            )}
          </div>
        </div>

        {/* ── Optional Dataset Upload ── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <p className="text-sm font-bold text-slate-800">Optional Dataset Upload</p>
              <p className="text-xs text-slate-400 mt-0.5">.sas7bdat · .xpt · .csv</p>
            </div>
            <button
              type="button"
              onClick={() => setDatasetEnabled(prev => !prev)}
              className={`w-12 h-6 rounded-full p-0.5 transition-colors flex-shrink-0 ${datasetEnabled ? 'bg-blue-600' : 'bg-slate-200'}`}
            >
              <span className={`block w-5 h-5 bg-white rounded-full shadow-sm transition-transform ${datasetEnabled ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          {datasetEnabled && (
            <div className="p-6 space-y-3">
              <div {...getDsRootProps()} className="border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-xl p-6 text-center cursor-pointer transition-colors">
                <input {...getDsInputProps()} />
                <Upload className="w-7 h-7 text-slate-400 mx-auto mb-2" />
                <p className="text-sm text-slate-500">Drop dataset files or click to browse</p>
              </div>
              {datasetFiles.length > 0 && (
                <div className="space-y-1.5">
                  {datasetFiles.map((f, i) => (
                    <div key={`${f.name}-${i}`} className="flex items-center gap-2.5 bg-slate-50 rounded-lg px-3 py-2">
                      <File className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      <span className="text-xs font-medium text-slate-700 flex-1 truncate">{f.name}</span>
                      <span className="text-[10px] text-slate-400">{(f.size / 1024).toFixed(1)} KB</span>
                      <button onClick={() => setDatasetFiles(prev => prev.filter((_, idx) => idx !== i))} className="text-slate-400 hover:text-red-500">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {datasetError && <p className="text-xs text-red-600">{datasetError}</p>}
            </div>
          )}
        </div>

        {/* ── Continue Button ── */}
        <button
          onClick={handleContinue}
          disabled={!canContinue}
          className="w-full flex items-center justify-center gap-2 px-5 py-3.5 bg-blue-600 text-white text-sm font-bold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
        >
          Continue to Input Preview
          <ArrowRight className="w-4 h-4" />
        </button>

      </div>
    </>
  );
};

export default UploadStep;
