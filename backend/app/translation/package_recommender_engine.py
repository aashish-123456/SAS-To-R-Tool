"""
Engine 4 — R/Package Recommender Engine  (Dynamic Edition)

Three-layer dynamic detection:
  Layer 1 — Function scan   : every SAS function Engine 1 detected → R equivalent + package
  Layer 2 — Construct scan  : structural keywords / flags (libname, merge, array…) → package
  Layer 3 — PROC scan       : every PROC type detected → best R package for that PROC

The engine never uses a fixed "capability" list.  It reads exactly what Engine 1
found in the code and maps each element to the optimal R package, then ranks by
simplicity and deduplicates.  Adding support for a new SAS function only requires
one line in SAS_FUNCTION_MAP below.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Optional

from .parser_engine import ParseResult
from .intent_engine import IntentResult
from .execution_flow_engine import FlowResult


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — SAS function  →  R function + package
# Every entry here is discovered automatically when Engine 1 detects the function.
# ══════════════════════════════════════════════════════════════════════════════

SAS_FUNCTION_MAP: Dict[str, Dict[str, Any]] = {

    # ── String manipulation ───────────────────────────────────────────────────
    "catx":      {"r_func": "paste(..., sep = '-')",         "package": "base",     "complexity": 1,
                  "note": "catx('-', a, b, c)  →  paste(a, b, c, sep='-')"},
    "cats":      {"r_func": "paste0(...)",                   "package": "base",     "complexity": 1,
                  "note": "cats(a, b)  →  paste0(a, b)"},
    "catt":      {"r_func": "paste0(...)",                   "package": "base",     "complexity": 1,
                  "note": "catt(a, b)  →  paste0(a, b)"},
    "cat":       {"r_func": "paste0(...)",                   "package": "base",     "complexity": 1,
                  "note": "cat(a, b)  →  paste0(a, b)"},
    "strip":     {"r_func": "trimws()",                      "package": "base",     "complexity": 1,
                  "note": "strip(x)  →  trimws(x)"},
    "trim":      {"r_func": "trimws(side='right')",          "package": "base",     "complexity": 1,
                  "note": "trim(x)  →  trimws(x, which='right')"},
    "upcase":    {"r_func": "toupper()",                     "package": "base",     "complexity": 1,
                  "note": "upcase(x)  →  toupper(x)"},
    "lowcase":   {"r_func": "tolower()",                     "package": "base",     "complexity": 1,
                  "note": "lowcase(x)  →  tolower(x)"},
    "propcase":  {"r_func": "str_to_title()",                "package": "stringr",  "complexity": 2,
                  "note": "propcase(x)  →  stringr::str_to_title(x)  (base: tools::toTitleCase)"},
    "substr":    {"r_func": "substr() / str_sub()",          "package": "base",     "complexity": 1,
                  "note": "substr(x,1,3)  →  substr(x,1,3)  or stringr::str_sub(x,1,3)"},
    "index":     {"r_func": "regexpr() / str_locate()",      "package": "base",     "complexity": 2,
                  "note": "index(x,'pat')  →  regexpr('pat',x)"},
    "scan":      {"r_func": "str_split_fixed()",             "package": "stringr",  "complexity": 2,
                  "note": "scan(x,2,' ')  →  str_split_fixed(x,' ',n)[,2]"},
    "tranwrd":   {"r_func": "str_replace_all()",             "package": "stringr",  "complexity": 2,
                  "note": "tranwrd(x,'old','new')  →  str_replace_all(x,'old','new')"},
    "compress":  {"r_func": "str_remove_all()",              "package": "stringr",  "complexity": 2,
                  "note": "compress(x)  →  str_remove_all(x,'\\\\s+')"},
    "left":      {"r_func": "str_pad(side='right')",         "package": "stringr",  "complexity": 1,
                  "note": "left(x)  →  trimws(x, 'left')"},
    "right":     {"r_func": "trimws(side='right')",          "package": "base",     "complexity": 1,
                  "note": "right(x)  →  trimws(x, 'right')"},
    "prxmatch":  {"r_func": "grepl() / str_detect()",        "package": "stringr",  "complexity": 3,
                  "note": "prxmatch('/pat/',x)  →  str_detect(x,'pat')"},
    "prxchange": {"r_func": "str_replace_all()",             "package": "stringr",  "complexity": 3,
                  "note": "prxchange('s/old/new/',x)  →  str_replace_all(x,'old','new')"},
    "anydigit":  {"r_func": "str_detect(., '[0-9]')",        "package": "stringr",  "complexity": 2,
                  "note": "anydigit(x)  →  str_detect(x,'[0-9]')"},
    "anyalpha":  {"r_func": "str_detect(., '[A-Za-z]')",     "package": "stringr",  "complexity": 2,
                  "note": "anyalpha(x)  →  str_detect(x,'[A-Za-z]')"},

    # ── Numeric / math ────────────────────────────────────────────────────────
    "abs":       {"r_func": "abs()",                         "package": "base",     "complexity": 1, "note": "abs(x)  →  abs(x)"},
    "ceil":      {"r_func": "ceiling()",                     "package": "base",     "complexity": 1, "note": "ceil(x)  →  ceiling(x)"},
    "floor":     {"r_func": "floor()",                       "package": "base",     "complexity": 1, "note": "floor(x)  →  floor(x)"},
    "round":     {"r_func": "round()",                       "package": "base",     "complexity": 1, "note": "round(x,2)  →  round(x,2)"},
    "int":       {"r_func": "as.integer() / trunc()",        "package": "base",     "complexity": 1, "note": "int(x)  →  as.integer(x)"},
    "mod":       {"r_func": "%% operator",                   "package": "base",     "complexity": 1, "note": "mod(a,b)  →  a %% b"},
    "sqrt":      {"r_func": "sqrt()",                        "package": "base",     "complexity": 1, "note": "sqrt(x)  →  sqrt(x)"},
    "log":       {"r_func": "log()",                         "package": "base",     "complexity": 1, "note": "log(x)  →  log(x)"},
    "log2":      {"r_func": "log2()",                        "package": "base",     "complexity": 1, "note": "log2(x)  →  log2(x)"},
    "log10":     {"r_func": "log10()",                       "package": "base",     "complexity": 1, "note": "log10(x)  →  log10(x)"},
    "exp":       {"r_func": "exp()",                         "package": "base",     "complexity": 1, "note": "exp(x)  →  exp(x)"},
    "sign":      {"r_func": "sign()",                        "package": "base",     "complexity": 1, "note": "sign(x)  →  sign(x)"},
    "sum":       {"r_func": "sum()",                         "package": "base",     "complexity": 1, "note": "sum(x,y)  →  sum(x,y,na.rm=TRUE)"},
    "mean":      {"r_func": "mean()",                        "package": "base",     "complexity": 1, "note": "mean(x)  →  mean(x,na.rm=TRUE)"},
    "min":       {"r_func": "min()",                         "package": "base",     "complexity": 1, "note": "min(x,y)  →  pmin(x,y)"},
    "max":       {"r_func": "max()",                         "package": "base",     "complexity": 1, "note": "max(x,y)  →  pmax(x,y)"},
    "range":     {"r_func": "diff(range())",                 "package": "base",     "complexity": 1, "note": "range(x)  →  diff(range(x,na.rm=TRUE))"},
    "std":       {"r_func": "sd()",                          "package": "base",     "complexity": 1, "note": "std(x)  →  sd(x,na.rm=TRUE)"},
    "var":       {"r_func": "var()",                         "package": "base",     "complexity": 1, "note": "var(x)  →  var(x,na.rm=TRUE)"},
    "median":    {"r_func": "median()",                      "package": "base",     "complexity": 1, "note": "median(x)  →  median(x,na.rm=TRUE)"},
    "n":         {"r_func": "n() / sum(!is.na())",           "package": "dplyr",    "complexity": 1, "note": "N (implicit count)  →  dplyr::n()"},
    "nmiss":     {"r_func": "sum(is.na())",                  "package": "base",     "complexity": 1, "note": "nmiss(x)  →  sum(is.na(x))"},
    "coalesce":  {"r_func": "coalesce()",                    "package": "dplyr",    "complexity": 2, "note": "coalesce(a,b)  →  dplyr::coalesce(a,b)"},
    "ifn":       {"r_func": "if_else()",                     "package": "dplyr",    "complexity": 1, "note": "ifn(cond,t,f)  →  dplyr::if_else(cond,t,f)"},
    "ifc":       {"r_func": "if_else()",                     "package": "dplyr",    "complexity": 1, "note": "ifc(cond,t,f)  →  dplyr::if_else(cond,t,f)"},

    # ── Date / time ───────────────────────────────────────────────────────────
    "put":       {"r_func": "format(as.Date(), '%Y-%m-%d')", "package": "base",     "complexity": 2,
                  "note": "put(dt, is8601da.)  →  format(as.Date(dt), '%Y-%m-%d')"},
    "input":     {"r_func": "as.Date() / as.numeric()",      "package": "base",     "complexity": 2,
                  "note": "input(x, yymmdd10.)  →  as.Date(x, '%Y-%m-%d')"},
    "today":     {"r_func": "Sys.Date()",                    "package": "base",     "complexity": 1, "note": "today()  →  Sys.Date()"},
    "date":      {"r_func": "Sys.Date()",                    "package": "base",     "complexity": 1, "note": "date()  →  Sys.Date()"},
    "year":      {"r_func": "year()",                        "package": "lubridate","complexity": 2, "note": "year(dt)  →  lubridate::year(dt)"},
    "month":     {"r_func": "month()",                       "package": "lubridate","complexity": 2, "note": "month(dt)  →  lubridate::month(dt)"},
    "day":       {"r_func": "day()",                         "package": "lubridate","complexity": 2, "note": "day(dt)  →  lubridate::day(dt)"},
    "hour":      {"r_func": "hour()",                        "package": "lubridate","complexity": 2, "note": "hour(dt)  →  lubridate::hour(dt)"},
    "minute":    {"r_func": "minute()",                      "package": "lubridate","complexity": 2, "note": "minute(dt)  →  lubridate::minute(dt)"},
    "second":    {"r_func": "second()",                      "package": "lubridate","complexity": 2, "note": "second(dt)  →  lubridate::second(dt)"},
    "datepart":  {"r_func": "as.Date()",                     "package": "base",     "complexity": 2, "note": "datepart(dt)  →  as.Date(dt)"},
    "timepart":  {"r_func": "format(dt, '%H:%M:%S')",        "package": "base",     "complexity": 2, "note": "timepart(dt)  →  format(dt, '%H:%M:%S')"},
    "intck":     {"r_func": "interval() / as.period()",      "package": "lubridate","complexity": 3, "note": "intck('month',a,b)  →  lubridate::interval(a,b) %/% months(1)"},
    "intnx":     {"r_func": "%m+% / %y+%",                  "package": "lubridate","complexity": 3, "note": "intnx('month',dt,3)  →  dt %m+% months(3)"},
    "datdif":    {"r_func": "as.numeric(difftime())",        "package": "base",     "complexity": 2, "note": "datdif(a,b,'ACT/ACT')  →  as.numeric(difftime(b,a,units='days'))"},
    "mdy":       {"r_func": "make_date()",                   "package": "lubridate","complexity": 2, "note": "mdy(m,d,y)  →  lubridate::make_date(y,m,d)"},
    "ymd":       {"r_func": "ymd()",                         "package": "lubridate","complexity": 2, "note": "ymd string  →  lubridate::ymd(x)"},

    # ── Lag / lead / cumulative ────────────────────────────────────────────────
    "lag":       {"r_func": "lag()",                         "package": "dplyr",    "complexity": 2, "note": "lag(x)  →  dplyr::lag(x)"},
    "dif":       {"r_func": "diff()",                        "package": "base",     "complexity": 2, "note": "dif(x)  →  diff(x)"},
    "first":     {"r_func": "first()",                       "package": "dplyr",    "complexity": 2, "note": "first.x  →  first() in group_by pipeline"},
    "last":      {"r_func": "last()",                        "package": "dplyr",    "complexity": 2, "note": "last.x  →  last() in group_by pipeline"},
}


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — SAS structural construct / keyword  →  R package
# Keyed by keywords Engine 1 flags or structural bool flags on ParseResult.
# ══════════════════════════════════════════════════════════════════════════════

SAS_CONSTRUCT_MAP: Dict[str, Dict[str, Any]] = {
    # File I/O
    "libname":   {"r_func": "read_sas() / write_sas()",  "package": "haven",    "complexity": 2,
                  "purpose": "Read / write SAS .sas7bdat datasets from disk (libname → haven::read_sas)"},
    "infile":    {"r_func": "read_delim()",               "package": "readr",    "complexity": 2,
                  "purpose": "Read raw delimited flat files (INFILE → readr::read_delim)"},
    "filename":  {"r_func": "file() / url()",             "package": "base",     "complexity": 2,
                  "purpose": "File reference (FILENAME → base R file connections)"},
    # DATA step variable operations — always need dplyr for mutate/select/filter
    "data":      {"r_func": "mutate() / select() / filter()", "package": "dplyr", "complexity": 2,
                  "purpose": "DATA step variable derivation and subsetting (→ dplyr mutate/select)"},
    "set":       {"r_func": "mutate()",                   "package": "dplyr",    "complexity": 2,
                  "purpose": "SET statement variable processing (→ dplyr mutate pipeline)"},
    "keep":      {"r_func": "select()",                   "package": "dplyr",    "complexity": 1,
                  "purpose": "KEEP statement (→ dplyr::select to retain only named columns)"},
    "drop":      {"r_func": "select(-col)",               "package": "dplyr",    "complexity": 1,
                  "purpose": "DROP statement (→ dplyr::select with minus sign to remove columns)"},
    "where":     {"r_func": "filter()",                   "package": "dplyr",    "complexity": 1,
                  "purpose": "WHERE clause (→ dplyr::filter)"},
    "output":    {"r_func": "filter() / bind_rows()",     "package": "dplyr",    "complexity": 2,
                  "purpose": "OUTPUT statement (→ dplyr::filter or bind_rows for multi-output)"},
    "by":        {"r_func": "group_by()",                 "package": "dplyr",    "complexity": 1,
                  "purpose": "BY-group processing (→ dplyr::group_by)"},
    # Dataset operations
    "merge":     {"r_func": "left_join() / inner_join()", "package": "dplyr",    "complexity": 2,
                  "purpose": "Dataset merging (MERGE BY → dplyr join verbs)"},
    "array":     {"r_func": "apply() / across()",         "package": "base",     "complexity": 3,
                  "purpose": "Array iteration across variables (ARRAY → apply / dplyr::across)"},
    "retain":    {"r_func": "cumsum() / lag()",           "package": "dplyr",    "complexity": 2,
                  "purpose": "Carry-forward / running totals (RETAIN → dplyr cumulative functions)"},
    # PROC equivalents
    "proc_means":    {"r_func": "group_by() + summarise()", "package": "dplyr",      "complexity": 2,
                      "purpose": "Descriptive statistics (PROC MEANS → dplyr summarise)"},
    "proc_summary":  {"r_func": "group_by() + summarise()", "package": "dplyr",      "complexity": 2,
                      "purpose": "Summary statistics (PROC SUMMARY → dplyr summarise, same as MEANS)"},
    "proc_freq":     {"r_func": "count()",                  "package": "dplyr",      "complexity": 2,
                      "purpose": "Frequency / cross-tab tables (PROC FREQ → dplyr::count)"},
    "proc_sort":     {"r_func": "arrange()",                "package": "dplyr",      "complexity": 1,
                      "purpose": "Sorting (PROC SORT → dplyr::arrange)"},
    "proc_print":    {"r_func": "print() / head()",         "package": "base",       "complexity": 1,
                      "purpose": "Display data (PROC PRINT → print)"},
    "proc_sql":      {"r_func": "join() / filter() / summarise()", "package": "dplyr","complexity": 3,
                      "purpose": "SQL queries (PROC SQL → dplyr verbs / sqldf)"},
    "proc_transpose":{"r_func": "pivot_wider() / pivot_longer()", "package": "tidyr", "complexity": 2,
                      "purpose": "Reshape data (PROC TRANSPOSE → tidyr pivots)"},
    "proc_reg":      {"r_func": "lm()",                     "package": "base",       "complexity": 2,
                      "purpose": "Linear regression (PROC REG → lm)"},
    "proc_glm":      {"r_func": "aov() / lm()",             "package": "base",       "complexity": 2,
                      "purpose": "ANOVA (PROC GLM → aov)"},
    "proc_logistic": {"r_func": "glm(family=binomial)",     "package": "stats",      "complexity": 3,
                      "purpose": "Logistic regression (PROC LOGISTIC → stats::glm family=binomial)"},
    "proc_mixed":    {"r_func": "lmer()",                   "package": "lme4",       "complexity": 4,
                      "purpose": "Mixed models (PROC MIXED → lme4::lmer — preferred over nlme)"},
    "proc_phreg":    {"r_func": "coxph()",                  "package": "survival",   "complexity": 3,
                      "purpose": "Cox regression (PROC PHREG → survival::coxph)"},
    "proc_lifetest": {"r_func": "survfit()",                "package": "survival",   "complexity": 3,
                      "purpose": "Kaplan-Meier (PROC LIFETEST → survival::survfit)"},
    "proc_import":   {"r_func": "read_delim() / read_excel() / read_sas()", "package": "readr", "complexity": 2,
                      "purpose": "Data import (PROC IMPORT → readr/readxl/haven readers)"},
    "proc_export":   {"r_func": "write.csv() / write_xlsx()","package": "base",      "complexity": 1,
                      "purpose": "Data export (PROC EXPORT → write.csv / writexl)"},
    "proc_univariate":{"r_func": "summary() / describe()",  "package": "base",       "complexity": 2,
                       "purpose": "Univariate stats (PROC UNIVARIATE → summary + shapiro.test)"},
    "proc_corr":     {"r_func": "cor()",                    "package": "base",       "complexity": 1,
                      "purpose": "Correlation (PROC CORR → cor)"},
    "proc_report":   {"r_func": "gt()",                     "package": "gt",         "complexity": 3,
                      "purpose": "Publication tables (PROC REPORT → gt::gt — HTML/PDF/Word output)"},
    "proc_tabulate": {"r_func": "tbl_summary()",            "package": "gtsummary",  "complexity": 2,
                      "purpose": "Summary tables (PROC TABULATE → gtsummary::tbl_summary)"},
    "proc_compare":  {"r_func": "all.equal() / compareDF()", "package": "base",      "complexity": 2,
                      "purpose": "Dataset comparison (PROC COMPARE → base::all.equal)"},
    "proc_contents": {"r_func": "str() / glimpse()",        "package": "base",       "complexity": 1,
                      "purpose": "Dataset metadata (PROC CONTENTS → base::str / dplyr::glimpse)"},
    "proc_format":   {"r_func": "factor() / labelled()",    "package": "haven",      "complexity": 2,
                      "purpose": "Value labels (PROC FORMAT → haven::labelled / base factor)"},
    "proc_fcmp":     {"r_func": "function()",               "package": "base",       "complexity": 3,
                      "purpose": "Custom functions (PROC FCMP → plain R functions)"},
}


# ══════════════════════════════════════════════════════════════════════════════
# Package metadata  (install instructions, descriptions)
# ══════════════════════════════════════════════════════════════════════════════

PACKAGE_META: Dict[str, Dict[str, str]] = {
    "dplyr":     {"desc": "Data manipulation — filter, mutate, arrange, join, summarise",   "cran": "https://cran.r-project.org/package=dplyr"},
    "tidyr":     {"desc": "Data reshaping — pivot_wider, pivot_longer, separate, unite",    "cran": "https://cran.r-project.org/package=tidyr"},
    "haven":     {"desc": "Read/write SAS, SPSS, Stata files (.sas7bdat, .xpt, write_xpt)","cran": "https://cran.r-project.org/package=haven"},
    "stringr":   {"desc": "String manipulation — str_to_title, str_replace_all, str_detect","cran": "https://cran.r-project.org/package=stringr"},
    "lubridate": {"desc": "Date/time arithmetic — ymd, mdy, year, month, day, interval",   "cran": "https://cran.r-project.org/package=lubridate"},
    "readr":     {"desc": "Fast flat-file reading — read_csv, read_delim, read_fwf",        "cran": "https://cran.r-project.org/package=readr"},
    "survival":  {"desc": "Survival analysis — coxph, survfit, Surv, survdiff",             "cran": "https://cran.r-project.org/package=survival"},
    "nlme":      {"desc": "Mixed effects models — lme, gls, intervals",                    "cran": "https://cran.r-project.org/package=nlme"},
    "lme4":      {"desc": "Mixed effects models (preferred) — lmer, glmer, isSingular",    "cran": "https://cran.r-project.org/package=lme4"},
    "stats":     {"desc": "Base statistical modelling — glm, lm, aov (ships with R)",      "cran": ""},
    "admiral":   {"desc": "ADaM dataset creation for clinical trials — derive_* functions", "cran": "https://cran.r-project.org/package=admiral"},
    "metacore":  {"desc": "CDISC metadata / Define.xml management for clinical submissions","cran": "https://cran.r-project.org/package=metacore"},
    "rtables":   {"desc": "Clinical TLF tables — tabulate_colcounts, analyze, build_table", "cran": "https://cran.r-project.org/package=rtables"},
    "gtsummary": {"desc": "Publication-ready summary tables — tbl_summary, tbl_regression","cran": "https://cran.r-project.org/package=gtsummary"},
    "gt":        {"desc": "Publication-quality HTML/PDF/Word tables — gt, cols_label",     "cran": "https://cran.r-project.org/package=gt"},
    "janitor":   {"desc": "Frequency / cross-tab tables, data cleaning — tabyl, clean_names","cran": "https://cran.r-project.org/package=janitor"},
    "tidyverse": {"desc": "Meta-package: dplyr + tidyr + stringr + lubridate + readr + ggplot2","cran": "https://cran.r-project.org/package=tidyverse"},
    "data.table":{"desc": "High-performance data manipulation (alternative to dplyr)",     "cran": "https://cran.r-project.org/package=data.table"},
    "knitr":     {"desc": "Formatted tables — kable",                                      "cran": "https://cran.r-project.org/package=knitr"},
    "writexl":   {"desc": "Write Excel files without Java dependency",                     "cran": "https://cran.r-project.org/package=writexl"},
    "ggplot2":   {"desc": "Data visualisation — plots, charts",                            "cran": "https://cran.r-project.org/package=ggplot2"},
    "purrr":     {"desc": "Functional programming — map, reduce, walk",                    "cran": "https://cran.r-project.org/package=purrr"},
    "glmnet":    {"desc": "Regularised regression — ridge, lasso, elastic net",            "cran": "https://cran.r-project.org/package=glmnet"},
    "broom":     {"desc": "Tidy model outputs — tidy, glance, augment",                   "cran": "https://cran.r-project.org/package=broom"},
    "emmeans":   {"desc": "Estimated marginal means (post-hoc contrasts for GLM/MIXED)",   "cran": "https://cran.r-project.org/package=emmeans"},
    "survminer": {"desc": "Kaplan-Meier visualisation — ggsurvplot",                       "cran": "https://cran.r-project.org/package=survminer"},
    "base":      {"desc": "Base R — always available, no installation needed",             "cran": ""},
}

# Preferred display order for the final package list
_PRIORITY = [
    "haven", "readr",
    "dplyr", "tidyr", "stringr", "lubridate",
    "admiral", "metacore", "rtables", "gtsummary",
    "survival", "lme4", "nlme", "stats", "glmnet",
    "gt", "janitor", "knitr", "writexl", "ggplot2",
    "broom", "emmeans", "survminer", "purrr",
    "data.table", "base",
]

# Clinical domain indicator variable patterns (SDTM / ADaM standards)
_CLINICAL_VAR_PATTERNS = {
    "USUBJID", "SUBJID", "STUDYID", "SITEID",
    "TRTEMFL", "AETERM", "AEDECOD", "AEBODSYS",
    "AESTDTC", "AEENDTC", "AESEV", "AESER",
    "PARAMCD", "PARAM", "AVAL", "BASE", "CHG", "PCHG",
    "VISITNUM", "VISIT", "ADT", "ADTM",
    "TRTSDT", "TRTEDT", "ARM", "ACTARM",
    "LBTEST", "LBTESTCD", "LBORRES", "LBSTRESN",
}


# ══════════════════════════════════════════════════════════════════════════════
# Data model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FunctionMapping:
    """One SAS function and its R equivalent."""
    sas_function: str
    r_function: str
    package: str
    note: str


@dataclass
class PackageInfo:
    name: str
    purpose: str
    functions_used: List[str]
    sas_functions_covered: List[str]   # which SAS functions this package handles
    complexity_score: float
    lines_estimate: int
    rationale: str
    alternatives: List[str] = field(default_factory=list)


@dataclass
class PackageRecommendation:
    primary_packages: List[PackageInfo]
    all_packages: List[str]
    alternatives: Dict[str, List[str]]
    install_code: str
    library_code: str
    selection_rationale: str
    package_function_map: Dict[str, List[str]]
    function_mappings: List[FunctionMapping]   # full SAS→R mapping table
    detection_layers: Dict[str, List[str]]     # which layer detected which package


# ══════════════════════════════════════════════════════════════════════════════
# Engine
# ══════════════════════════════════════════════════════════════════════════════

class PackageRecommenderEngine:
    """
    Engine 4 — Dynamic R/Package Recommender.

    Scans four layers of Engine 1 output:
      Layer 1  SAS functions detected  →  SAS_FUNCTION_MAP
      Layer 2  Keywords / flags        →  SAS_CONSTRUCT_MAP
      Layer 3  PROC types detected     →  SAS_CONSTRUCT_MAP (proc_ prefix)
      Layer 4  Clinical domain signals →  admiral / metacore / rtables / haven(xpt)

    Each discovered element maps to an R package.  Packages are deduplicated,
    ranked by simplicity, and the result is fully self-installing in R.
    """

    def recommend(
        self,
        parse_result: ParseResult,
        intent_result: IntentResult,
        flow_result: FlowResult,
    ) -> PackageRecommendation:

        # ── Run four detection layers ─────────────────────────────────────────
        layer1_pkgs, fn_mappings = self._layer1_functions(parse_result)
        layer2_pkgs              = self._layer2_constructs(parse_result)
        layer3_pkgs              = self._layer3_procs(parse_result)
        layer4_pkgs              = self._layer4_clinical(parse_result, intent_result)

        detection_layers = {
            "layer1_function_scan":  sorted(layer1_pkgs.keys()),
            "layer2_construct_scan": sorted(layer2_pkgs.keys()),
            "layer3_proc_scan":      sorted(layer3_pkgs.keys()),
            "layer4_clinical_scan":  sorted(layer4_pkgs.keys()),
        }

        # ── Merge all layers ──────────────────────────────────────────────────
        merged = self._merge(layer1_pkgs, layer2_pkgs, layer3_pkgs, layer4_pkgs)

        # ── Build ordered package list ────────────────────────────────────────
        all_names = self._order(merged)

        installable  = [n for n in all_names if n != "base"]
        install_code = self._install_code(installable)
        library_code = self._library_code(all_names)
        rationale    = self._rationale(merged, parse_result, fn_mappings)

        primary_packages = [
            PackageInfo(
                name                 = name,
                purpose              = PACKAGE_META.get(name, {}).get("desc", ""),
                functions_used       = merged[name]["r_functions"],
                sas_functions_covered= merged[name]["sas_functions"],
                complexity_score     = float(merged[name]["complexity"]),
                lines_estimate       = merged[name]["lines_estimate"],
                rationale            = merged[name]["rationale"],
                alternatives         = merged[name].get("alternatives", []),
            )
            for name in all_names
            if name in merged
        ]

        return PackageRecommendation(
            primary_packages     = primary_packages,
            all_packages         = all_names,
            alternatives         = {name: merged[name].get("alternatives", [])
                                    for name in all_names if name in merged},
            install_code         = install_code,
            library_code         = library_code,
            selection_rationale  = rationale,
            package_function_map = {name: merged[name]["r_functions"] for name in all_names if name in merged},
            function_mappings    = fn_mappings,
            detection_layers     = detection_layers,
        )

    # ── Layer 1: SAS functions ────────────────────────────────────────────────

    def _layer1_functions(
        self, pr: ParseResult
    ):
        pkg_map: Dict[str, Dict] = {}
        mappings: List[FunctionMapping] = []

        for fn in pr.functions:
            fn_lc = fn.lower()
            entry = SAS_FUNCTION_MAP.get(fn_lc)
            if not entry:
                continue

            pkg  = entry["package"]
            note = entry.get("note", "")

            mappings.append(FunctionMapping(
                sas_function = fn,
                r_function   = entry["r_func"],
                package      = pkg,
                note         = note,
            ))

            if pkg not in pkg_map:
                pkg_map[pkg] = self._new_entry(pkg)
            pkg_map[pkg]["r_functions"].append(entry["r_func"])
            pkg_map[pkg]["sas_functions"].append(fn)
            pkg_map[pkg]["complexity"] = max(
                pkg_map[pkg]["complexity"], entry.get("complexity", 1)
            )
            pkg_map[pkg]["lines_estimate"] += 2

        return pkg_map, mappings

    # ── Layer 2: Structural keywords / flags ──────────────────────────────────

    def _layer2_constructs(self, pr: ParseResult) -> Dict[str, Dict]:
        pkg_map: Dict[str, Dict] = {}

        # Scan keywords Engine 1 detected
        for kw in pr.keywords:
            entry = SAS_CONSTRUCT_MAP.get(kw.lower())
            if entry:
                self._add_construct(pkg_map, entry, kw)

        # Scan boolean flags
        flag_to_construct = {
            pr.has_merge:          "merge",
            pr.has_array:          "array",
            pr.has_retain:         "retain",
            pr.has_sql:            "proc_sql",
            pr.has_proc_mixed:     "proc_mixed",
            pr.has_clinical_procs: None,   # handled by layer 3
        }
        for flag, construct in flag_to_construct.items():
            if flag and construct:
                entry = SAS_CONSTRUCT_MAP.get(construct)
                if entry:
                    self._add_construct(pkg_map, entry, construct)

        # libname specifically → haven
        if "libname" in pr.keywords:
            entry = SAS_CONSTRUCT_MAP["libname"]
            self._add_construct(pkg_map, entry, "libname")

        # Date arithmetic detected: variable names ending in DT/DTM/DTC, or date
        # format keywords in the source code → lubridate is needed
        _date_var_suffixes = ("dt", "dtm", "dtc", "date", "stdt", "endt", "rfstdt")
        _date_fmt_keywords = {"yymmdd", "mmddyy", "ddmmyy", "is8601", "datetime",
                               "date9", "date7", "anydtdte", "julian"}
        has_date_vars = any(
            v.lower().endswith(_date_var_suffixes) for v in pr.variables
        )
        has_date_fmts = bool(_date_fmt_keywords & {kw.lower() for kw in pr.keywords})
        if (has_date_vars or has_date_fmts) and "lubridate" not in pkg_map:
            pkg_map["lubridate"] = self._new_entry("lubridate")
            pkg_map["lubridate"]["r_functions"].append("as.Date() / ymd() / interval()")
            pkg_map["lubridate"]["sas_functions"].append("date arithmetic / date variables")
            pkg_map["lubridate"]["rationale"] = (
                "Date variables detected — lubridate provides as.Date(), ymd(), "
                "interval() and arithmetic that safely handles study-day calculations."
            )

        return pkg_map

    # ── Layer 3: PROC types ───────────────────────────────────────────────────

    def _layer3_procs(self, pr: ParseResult) -> Dict[str, Dict]:
        pkg_map: Dict[str, Dict] = {}

        for proc_type in pr.proc_types:
            key   = f"proc_{proc_type.lower()}"
            entry = SAS_CONSTRUCT_MAP.get(key)
            if entry:
                self._add_construct(pkg_map, entry, key)

            # Special handling for PROC IMPORT — add readr, readxl, haven
            if proc_type.lower() == 'import':
                for pkg in ['readr', 'readxl', 'haven']:
                    if pkg not in pkg_map:
                        pkg_map[pkg] = self._new_entry(pkg)
                    if pkg == 'readr':
                        pkg_map[pkg]["r_functions"].append("read_delim() / read_csv()")
                        pkg_map[pkg]["purpose"] = "Read delimited files (CSV, TSV)"
                    elif pkg == 'readxl':
                        pkg_map[pkg]["r_functions"].append("read_excel()")
                        pkg_map[pkg]["purpose"] = "Read Excel files (.xlsx)"
                    elif pkg == 'haven':
                        pkg_map[pkg]["r_functions"].append("read_sas() / read_xpt()")
                        pkg_map[pkg]["purpose"] = "Read SAS and XPT transport files"

        return pkg_map

    # ── Layer 4: Clinical domain (CDISC / ADaM / SDTM) ───────────────────────

    def _layer4_clinical(self, pr: ParseResult, ir: IntentResult) -> Dict[str, Dict]:
        pkg_map: Dict[str, Dict] = {}

        # Detect clinical signals from multiple sources
        domain = getattr(ir, "problem_domain", "")
        is_clinical = (
            pr.has_clinical_procs
            or domain == "clinical"
            or any(v.upper() in _CLINICAL_VAR_PATTERNS for v in pr.variables)
        )

        if not is_clinical:
            return pkg_map

        # ADaM domain presence → admiral
        adam_domains = {"ADSL", "ADAE", "ADLB", "ADCM", "ADEX", "ADMH", "ADVS", "ADTTE"}
        has_adam = any(
            ds.upper() in adam_domains or ds.upper().startswith("AD")
            for ds in pr.datasets
        )
        if has_adam:
            if "admiral" not in pkg_map:
                pkg_map["admiral"] = self._new_entry("admiral")
            pkg_map["admiral"]["r_functions"].append("derive_vars_dt() / derive_param_computed()")
            pkg_map["admiral"]["sas_functions"].append("ADaM dataset creation")
            pkg_map["admiral"]["complexity"] = 4
            pkg_map["admiral"]["rationale"] = (
                "ADaM dataset(s) detected — admiral provides derive_* functions that "
                "replicate SAS DATA step ADaM derivations with full CDISC compliance."
            )

        # XPT transport output → haven::write_xpt (already via libname, but add explicit note)
        xpt_signals = {"xpt", "transport", "xport"}
        if any(kw.lower() in xpt_signals for kw in pr.keywords):
            if "haven" not in pkg_map:
                pkg_map["haven"] = self._new_entry("haven")
            pkg_map["haven"]["r_functions"].append("write_xpt()")
            pkg_map["haven"]["sas_functions"].append("XPT transport output")

        # TLF / PROC REPORT / PROC TABULATE patterns → rtables
        tlf_procs = {"report", "tabulate", "print"}
        if any(pt.lower() in tlf_procs for pt in pr.proc_types) or pr.has_clinical_procs:
            if "rtables" not in pkg_map:
                pkg_map["rtables"] = self._new_entry("rtables")
            pkg_map["rtables"]["r_functions"].append("build_table() / tabulate_colcounts()")
            pkg_map["rtables"]["sas_functions"].append("Clinical TLF output")
            pkg_map["rtables"]["complexity"] = 3
            pkg_map["rtables"]["rationale"] = (
                "Clinical output procedures detected — rtables generates submission-ready "
                "TLF tables with proper pagination and formatting for regulatory packages."
            )

        # Define.xml / metadata → metacore
        meta_signals = {"define", "metadata", "cdisc", "sdtm"}
        if any(kw.lower() in meta_signals for kw in pr.keywords):
            if "metacore" not in pkg_map:
                pkg_map["metacore"] = self._new_entry("metacore")
            pkg_map["metacore"]["r_functions"].append("metacore() / select_dataset()")
            pkg_map["metacore"]["sas_functions"].append("Define.xml / CDISC metadata")
            pkg_map["metacore"]["complexity"] = 3

        return pkg_map

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _new_entry(self, pkg: str) -> Dict:
        return {
            "r_functions":    [],
            "sas_functions":  [],
            "complexity":     1,
            "lines_estimate": 5,
            "rationale":      PACKAGE_META.get(pkg, {}).get("desc", ""),
            "alternatives":   [],
        }

    def _add_construct(self, pkg_map: Dict, entry: Dict, label: str) -> None:
        pkg = entry["package"]
        if pkg not in pkg_map:
            pkg_map[pkg] = self._new_entry(pkg)
        r_fn = entry.get("r_func", "")
        if r_fn and r_fn not in pkg_map[pkg]["r_functions"]:
            pkg_map[pkg]["r_functions"].append(r_fn)
        if label not in pkg_map[pkg]["sas_functions"]:
            pkg_map[pkg]["sas_functions"].append(label)
        pkg_map[pkg]["complexity"] = max(
            pkg_map[pkg]["complexity"], entry.get("complexity", 1)
        )
        pkg_map[pkg]["lines_estimate"] += 3

    def _merge(self, *layers: Dict[str, Dict]) -> Dict[str, Dict]:
        merged: Dict[str, Dict] = {}
        for layer in layers:
            for pkg, info in layer.items():
                if pkg not in merged:
                    merged[pkg] = self._new_entry(pkg)
                for fn in info["r_functions"]:
                    if fn not in merged[pkg]["r_functions"]:
                        merged[pkg]["r_functions"].append(fn)
                for sf in info["sas_functions"]:
                    if sf not in merged[pkg]["sas_functions"]:
                        merged[pkg]["sas_functions"].append(sf)
                merged[pkg]["complexity"] = max(
                    merged[pkg]["complexity"], info["complexity"]
                )
                merged[pkg]["lines_estimate"] += info["lines_estimate"]
        return merged

    def _order(self, merged: Dict[str, Dict]) -> List[str]:
        ordered: List[str] = []
        for pkg in _PRIORITY:
            if pkg in merged:
                ordered.append(pkg)
        for pkg in merged:
            if pkg not in ordered:
                ordered.append(pkg)
        return ordered

    # ── Code generation ────────────────────────────────────────────────────────

    def _install_code(self, packages: List[str]) -> str:
        if not packages:
            return "# No additional packages required — using base R only.\n"
        pkg_list = ", ".join(f'"{p}"' for p in packages)
        return (
            "# ── Auto-install required packages ──────────────────────────────────\n"
            f"required_packages <- c({pkg_list})\n"
            "missing_packages <- required_packages[\n"
            "  !(required_packages %in% installed.packages()[, \"Package\"])\n"
            "]\n"
            "if (length(missing_packages) > 0) {\n"
            "  install.packages(missing_packages,\n"
            "                   repos = \"https://cloud.r-project.org\",\n"
            "                   quiet = TRUE)\n"
            "  cat(\"Installed:\", paste(missing_packages, collapse = \", \"), \"\\n\")\n"
            "}\n"
        )

    def _library_code(self, packages: List[str]) -> str:
        loadable = [p for p in packages if p != "base"]
        if not loadable:
            return "# Using base R only — no library() calls needed."
        lines = "\n".join(f"library({p})" for p in loadable)
        return f"# ── Load libraries ───────────────────────────────────────────────────\n{lines}"

    def _rationale(
        self,
        merged: Dict[str, Dict],
        pr: ParseResult,
        fn_mappings: List[FunctionMapping],
    ) -> str:
        non_base = [p for p in merged if p != "base"]
        if not non_base:
            return "No external packages required — pure base R translation."

        clinical_pkgs = [p for p in non_base if p in {"admiral", "metacore", "rtables", "gtsummary", "gt"}]
        lines = [f"Dynamic analysis selected {len(non_base)} package(s): {', '.join(non_base)}."]
        lines.append(f"Based on {len(fn_mappings)} SAS function(s) and {len(pr.proc_types)} PROC type(s) detected.")
        if clinical_pkgs:
            lines.append(f"Clinical domain packages added (Layer 4): {', '.join(clinical_pkgs)}.")

        for pkg in non_base[:5]:
            sas_fns = merged[pkg]["sas_functions"]
            r_fns   = merged[pkg]["r_functions"]
            lines.append(
                f"  {pkg}: covers SAS [{', '.join(sas_fns[:4])}] "
                f"→ R [{', '.join(r_fns[:3])}]"
            )

        total_lines = sum(m["lines_estimate"] for m in merged.values())
        lines.append(f"Estimated R code size: ~{total_lines} lines.")
        return "\n".join(lines)
