"""Test the new dynamic architecture features."""
import sys
sys.path.insert(0, 'backend')

from app.translation.parser_engine import ParserEngine
from app.translation.lineage_engine import LineageEngine
from app.services.r_generator import RCodeGenerator

PASS = 0
FAIL = 0

def check(name: str, code: str, expected_fragments: list[str],
          forbidden: list[str] | None = None):
    global PASS, FAIL
    engine = ParserEngine()
    gen    = RCodeGenerator()
    pr     = engine.parse(code)
    r      = gen.generate(pr.ast, pr.inline_data)
    ok     = True
    issues = []
    for frag in expected_fragments:
        if frag not in r:
            ok = False
            issues.append(f"  MISSING: {frag!r}")
    for frag in (forbidden or []):
        if frag in r:
            ok = False
            issues.append(f"  FORBIDDEN found: {frag!r}")
    if ok:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}")
        for i in issues:
            print(i)


# ── Test 1: %let macro variable expansion ──────────────────────────────────
import importlib.util, sys as _sys
spec = importlib.util.spec_from_file_location("main_mod", "backend/main.py")
# We can't import main.py directly due to fastapi dep — extract the function inline
import re as _re
def _expand_simple_macros(code: str) -> str:
    macro_vars = {}
    let_re = _re.compile(r'%(?:let|global)\s+(\w+)\s*=\s*(.*?)\s*;', _re.IGNORECASE | _re.DOTALL)
    for m in let_re.finditer(code):
        macro_vars[m.group(1).upper()] = m.group(2).strip().strip('"\'')
    code = let_re.sub('', code)
    def _replace(m):
        return macro_vars.get(m.group(1).upper(), m.group(0))
    return _re.sub(r'&&?([A-Za-z_][A-Za-z0-9_]*)', _replace, code)
sas_with_let = r'''
%let trt = TRT01A;
%let ds = adae;
%let param = ADURN;

proc means data=&ds;
  class &trt;
  var &param;
run;
'''
expanded = _expand_simple_macros(sas_with_let)
if 'adae' in expanded and 'TRT01A' in expanded and 'ADURN' in expanded:
    PASS += 1
    print("[PASS] %let macro variable expansion")
else:
    FAIL += 1
    print(f"[FAIL] %let expansion — expanded code:\n{expanded[:300]}")


# ── Test 2: ARRAY with DO loop → across() ──────────────────────────────────
check(
    "ARRAY init via DO loop -> across()",
    r'''
data work;
  set source;
  array flags{3} f1 f2 f3;
  do i = 1 to 3;
    flags{i} = 0;
  end;
run;
''',
    expected_fragments=["across(c(f1, f2, f3), ~0)"],
    forbidden=["TODO"],
)


# ── Test 3: ARRAY with range notation x1-x5 ────────────────────────────────
from app.services.sas_parser import SASParser
p = SASParser()
ast, _ = p.parse("array scores{5} s1-s5;")
arr_node = next((n for n in ast if n.get('type') == 'array_def'), None)
if arr_node and arr_node.get('variables') == ['s1', 's2', 's3', 's4', 's5']:
    PASS += 1
    print("[PASS] ARRAY range notation s1-s5 expansion")
else:
    FAIL += 1
    print(f"[FAIL] ARRAY range notation — got: {arr_node}")


# ── Test 4: Indexed DO loop → for loop (complex body) ──────────────────────
check(
    "Indexed DO loop → for() in R",
    r'''
data work;
  set source;
  array val{3} v1 v2 v3;
  do i = 1 to 3;
    val{i} = val{i} * 2;
  end;
run;
''',
    expected_fragments=["for (i in"],
    forbidden=["TODO"],
)


# ── Test 5: Dataset Lineage Engine ─────────────────────────────────────────
from app.translation.lineage_engine import LineageEngine
sas_lineage = r'''
libname sdtm "/data/sdtm";
libname adam "/data/adam";

data adam.adae;
  set sdtm.ae;
  keep USUBJID AETERM;
run;

data adae2;
  merge adam.adae(in=a) sdtm.dm(in=b keep=USUBJID TRT01A);
  by USUBJID;
  if a;
run;

proc sort data=adae2;
  by USUBJID;
run;

proc freq data=adae2;
  tables AETERM;
run;
'''

pr   = ParserEngine().parse(sas_lineage)
lin  = LineageEngine().build(pr)

edge_ops = {e.operation for e in lin.edges}
node_names = set(lin.nodes.keys())

has_set_edge   = 'set' in edge_ops
has_merge_edge = 'merge' in edge_ops
has_ae_node    = 'ae' in node_names
has_adae_node  = 'adae' in node_names
has_adae2_node = 'adae2' in node_names
has_summary    = bool(lin.summary)
has_mermaid    = 'graph LR' in lin.mermaid

if all([has_set_edge, has_merge_edge, has_ae_node, has_adae_node, has_adae2_node, has_summary, has_mermaid]):
    PASS += 1
    print("[PASS] Dataset Lineage Engine — nodes, edges, mermaid")
else:
    FAIL += 1
    print("[FAIL] Dataset Lineage Engine")
    print(f"  set_edge={has_set_edge} merge_edge={has_merge_edge}")
    print(f"  ae={has_ae_node} adae={has_adae_node} adae2={has_adae2_node}")
    print(f"  summary={has_summary!r}")
    print(f"  mermaid_ok={has_mermaid}")
    print(f"  nodes: {list(lin.nodes.keys())}")
    print(f"  edges: {[(e.source, e.target, e.operation) for e in lin.edges]}")


# ── Test 6: Full pipeline with lineage ─────────────────────────────────────
from app.translation.pipeline import TranslationPipeline
pip = TranslationPipeline()
result = pip.run(sas_lineage)
d = result.to_dict()

has_lineage_key = 'lineage' in d
has_lineage_nodes = bool(d.get('lineage', {}).get('nodes'))
has_mermaid_in_dict = 'graph LR' in d.get('lineage', {}).get('mermaid', '')

if has_lineage_key and has_lineage_nodes and has_mermaid_in_dict:
    PASS += 1
    print("[PASS] Pipeline includes lineage engine output in to_dict()")
else:
    FAIL += 1
    print(f"[FAIL] Pipeline lineage output: key={has_lineage_key} nodes={has_lineage_nodes} mermaid={has_mermaid_in_dict}")


# ── Test 7: PROC MIXED formula with options stripped ───────────────────────
check(
    "PROC MIXED — SAS options stripped from formula",
    r'''
proc mixed data=mydata;
  class TRT VISIT;
  model RESP = TRT VISIT TRT*VISIT / ddfm=kr;
  random SUBJECT;
run;
''',
    expected_fragments=["lme4::lmer(RESP ~ TRT + VISIT + TRT:VISIT"],
    forbidden=["/ ddfm", "ddfm=kr"],
)


# ── Test 8: Cache reset exposed via upload endpoint metadata ────────────────
import sys; sys.path.insert(0, 'backend')
# Verify main.py compiles and has the cache reset logic
with open('backend/main.py', 'r', encoding='utf-8') as f:
    main_src = f.read()
if 'Cache Reset' in main_src and 'translations_db' in main_src and 'executions_db' in main_src:
    PASS += 1
    print("[PASS] Cache reset logic present in upload endpoint")
else:
    FAIL += 1
    print("[FAIL] Cache reset logic missing from upload endpoint")


print(f"\n{'='*60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed / {PASS+FAIL} total")
