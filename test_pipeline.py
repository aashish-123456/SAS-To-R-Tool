"""Full pipeline smoke test."""
import sys
sys.path.insert(0, 'backend')
from app.translation.pipeline import TranslationPipeline

sas = r'''
libname adam "/data/adam";
data adam.adae;
  set sdtm.ae;
  TRTEMFL = "1";
  if AESER = "Y" then AESERFLI = 1;
  else AESERFLI = 0;
  ASTDT = input(AESTDTC, is8601da.);
  ADURN = AENDT - ASTDT + 1;
  keep USUBJID TRTEMFL AESERFLI ASTDT ADURN AETERM AEBODSYS;
run;

proc freq data=adam.adae;
  tables AEBODSYS / nocum;
run;

proc means data=adam.adae n mean std;
  class AEBODSYS;
  var ADURN;
run;

proc logistic data=adam.adae;
  model AESERFLI = ADURN;
run;
'''

pipeline = TranslationPipeline()
result = pipeline.run(sas).to_dict()

tr = result.get('translation', {})
vr = result.get('validation', {})

print('r_code lines :', len(tr.get('r_code', '').splitlines()))
print('packages     :', tr.get('packages_used'))
print('warnings     :', tr.get('warnings', []))
print('notes        :', tr.get('translation_notes', []))
print('equivalence  :', vr.get('estimated_equivalence_pct'), '%')
print('approval     :', vr.get('approval_status'))
print()
print('=== R CODE (first 80 lines) ===')
for i, line in enumerate(tr.get('r_code', '').splitlines()[:80], 1):
    print(f'{i:3}: {line}')
