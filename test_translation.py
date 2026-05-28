"""Comprehensive translation test for clinical SAS code."""
import sys
sys.path.insert(0, 'backend')

from app.translation.parser_engine import ParserEngine
from app.services.r_generator import RCodeGenerator

# ── Test 1: Full clinical ADAE pipeline ──────────────────────────────────────
SAS_ADAE = r'''
libname sdtm "/data/sdtm";
libname adam "/data/adam";

data adam.adae;
  set sdtm.ae;
  TRTEMFL = "1";
  if AESER = "Y" then AESERFLI = 1;
  else AESERFLI = 0;
  TRTSDT = input(RFSTDTC, is8601da.);
  ASTDT  = input(AESTDTC, is8601da.);
  AENDT  = input(AEENDTC, is8601da.);
  ADURN  = AENDT - ASTDT + 1;
  AETERM_UPPER = upcase(AETERM);
  SUBJID = substr(USUBJID, 1, 10);
  keep USUBJID TRTEMFL AESERFLI TRTSDT ASTDT AENDT ADURN AETERM AETERM_UPPER AEBODSYS SUBJID;
run;

data adae_merged;
  merge adam.adae(in=a) sdtm.dm(in=b keep=USUBJID TRT01A SITEID);
  by USUBJID;
  if a;
run;

proc freq data=adae_merged;
  tables AEBODSYS*AETERM / nocum nopercent;
run;

proc means data=adae_merged n mean std min max;
  class TRT01A;
  var ADURN;
run;

proc sort data=adae_merged;
  by USUBJID ASTDT;
run;

proc logistic data=adae_merged descending;
  model AESERFLI = ADURN TRT01A;
run;
'''

# ── Test 2: ADTTE survival analysis ─────────────────────────────────────────
SAS_ADTTE = r'''
libname adam "/data/adam";

data adam.adtte;
  set adam.adsl;
  PARAMCD = "OS";
  PARAM   = "Overall Survival";
  ADT     = input(DTHDT, is8601da.);
  TRTSDT  = input(TRTSDT, is8601da.);
  AVAL    = ADT - TRTSDT + 1;
  if DTHFL = "Y" then CNSR = 0;
  else CNSR = 1;
  keep USUBJID PARAMCD PARAM AVAL CNSR TRT01A;
run;

proc phreg data=adam.adtte;
  class TRT01A;
  model AVAL*CNSR(1) = TRT01A;
  hazardratio TRT01A;
run;

proc lifetest data=adam.adtte method=km;
  time AVAL*CNSR(1);
  strata TRT01A;
run;
'''

# ── Test 3: Mixed effects model ──────────────────────────────────────────────
SAS_MIXED = r'''
proc mixed data=mydata;
  class TRT VISIT SUBJECT;
  model RESPONSE = TRT VISIT TRT*VISIT / ddfm=satterthwaite;
  random SUBJECT;
  lsmeans TRT*VISIT / diff cl;
run;
'''

# ── Test 4: Import and transpose ─────────────────────────────────────────────
SAS_IMPORT = r'''
proc import datafile="/data/raw/ae_data.csv"
  out=ae_raw
  dbms=csv
  replace;
  getnames=yes;
run;

proc transpose data=ae_raw out=ae_wide prefix=VISIT;
  by USUBJID;
  id VISIT;
  var AVAL;
run;
'''

# ── Test 5: RETAIN with DO block ─────────────────────────────────────────────
SAS_RETAIN = r'''
data cumulative;
  set events;
  retain cumsum 0;
  cumsum = cumsum + events_count;
  if category = "A" then do;
    label_a = "Category A";
    flag_a = 1;
  end;
  else do;
    label_a = "Other";
    flag_a = 0;
  end;
run;
'''

# ── Test 6: PROC CONTENTS + COMPARE ─────────────────────────────────────────
SAS_COMPARE = r'''
proc contents data=mydata;
run;

proc compare base=expected compare=actual listall;
run;
'''

engine = ParserEngine()
gen    = RCodeGenerator()

tests = [
    ("ADAE Clinical Pipeline", SAS_ADAE),
    ("ADTTE Survival Analysis", SAS_ADTTE),
    ("PROC MIXED",             SAS_MIXED),
    ("Import + Transpose",     SAS_IMPORT),
    ("RETAIN + DO blocks",     SAS_RETAIN),
    ("CONTENTS + COMPARE",     SAS_COMPARE),
]

PASS = 0
FAIL = 0

for name, sas in tests:
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print('='*70)
    try:
        pr     = engine.parse(sas)
        r_code = gen.generate(pr.ast, pr.inline_data)
        # Basic quality checks
        issues = []
        if "TODO" in r_code:
            todos = [l.strip() for l in r_code.splitlines() if "TODO" in l]
            issues.append(f"  TODOs remaining: {todos}")
        if r_code.strip() == "":
            issues.append("  EMPTY output!")
        if "library(dplyr)" not in r_code and "library(haven)" not in r_code:
            issues.append("  No library imports")

        print(r_code)
        if issues:
            print("\n[WARNINGS]")
            for i in issues: print(i)
            FAIL += 1
        else:
            print("\n[PASS]")
            PASS += 1
    except Exception as e:
        import traceback
        print(f"[ERROR] {e}")
        traceback.print_exc()
        FAIL += 1

print(f"\n{'='*70}")
print(f"RESULTS: {PASS} passed, {FAIL} failed / {len(tests)} total")
