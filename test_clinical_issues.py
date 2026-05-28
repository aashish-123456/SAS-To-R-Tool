"""Concrete clinical SAS translation tests for the 8 reported issues."""
import sys
sys.path.insert(0, 'backend')

from app.translation.parser_engine import ParserEngine
from app.services.r_generator import RCodeGenerator

def translate(sas_code):
    engine = ParserEngine()
    gen = RCodeGenerator()
    pr = engine.parse(sas_code)
    return gen.generate(pr.ast, pr.inline_data)

# ── Test A: data sdtm.ae; set raw.ae_raw; assignments → should create ae not adae
sas_a = r'''
libname raw "/projects/raw";
libname sdtm "/projects/sdtm";

data sdtm.ae;
  set raw.ae_raw;
  STUDYID = "XYZ101";
  DOMAIN = "AE";
  USUBJID = catx('-', STUDYID, SITEID, SUBJID);
  AESEQ = _N_;
  AETERM = strip(AE_TERM);
  AEDECOD = strip(MEDDRA_PT);
  AESER = upcase(SERIOUS);
  AESEV = propcase(SEVERITY);
run;
'''
r_a = translate(sas_a)
print("=== Output for data sdtm.ae; set raw.ae_raw; ===")
print(r_a)
print()

# ── Test B: MERGE with keep= option
sas_b = r'''
libname sdtm "/projects/sdtm";
libname adam "/projects/adam";

data adam.adae;
  merge sdtm.ae(in=a) dm(keep=USUBJID RFSTDTC TRT01A);
  by USUBJID;
  if a;
run;
'''
r_b = translate(sas_b)
print("=== Output for MERGE with keep= ===")
print(r_b)
print()

# ── Test C: Date subtraction
sas_c = r'''
data work.dates;
  set source;
  ASTDY = ASTDT - RFSTDT + (ASTDT >= RFSTDT);
run;
'''
r_c = translate(sas_c)
print("=== Output for date subtraction ===")
print(r_c)
print()

# ── Test D: Unknown statement fallback (TODO check)
sas_d = r'''
data work.test;
  set source;
  output;
  some_weird_sas_statement x y z;
run;
'''
r_d = translate(sas_d)
print("=== Output with unknown statement ===")
print(r_d)
todos = [l for l in r_d.splitlines() if 'TODO' in l]
print(f"TODO lines: {todos}")
print()

# ── Test E: Data step dataset name check (sdtm.ae → ae, not adae)
import re
lines_a = [l.strip() for l in r_a.splitlines()]
dataset_assign_lines = [l for l in lines_a if re.match(r'^ae\s*<-', l)]
adae_lines = [l for l in lines_a if re.match(r'^adae\s*<-', l)]
studyid_as_global = [l for l in lines_a if l.startswith('STUDYID <-')]
print("=== Issue checks ===")
print(f"Lines creating ae: {dataset_assign_lines}")
print(f"Lines creating adae (should be NONE): {adae_lines}")
print(f"STUDYID as global (should be NONE): {studyid_as_global}")
studyid_in_mutate = [l for l in lines_a if 'STUDYID' in l and 'mutate' in l]
print(f"STUDYID in mutate (should exist): {studyid_in_mutate}")
print()

# ── Test F: MERGE keep= parsing check
print("=== MERGE keep= check ===")
select_lines = [l.strip() for l in r_b.splitlines() if 'select' in l.lower()]
print(f"select() lines: {select_lines}")
print()
