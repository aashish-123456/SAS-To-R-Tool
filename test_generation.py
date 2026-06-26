#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from app.services.sas_parser import SASParser
from app.services.r_generator import RCodeGenerator

# Read the test SAS file
with open('backend/data/uploads/041b8338-d58c-4873-a0dc-6a0433947e15_sas_15c9c78a-bd56-401d-97d6-9d381d7d8d63_Sas1.txt', 'r') as f:
    sas_code = f.read()

print("=" * 80)
print("PARSING SAS CODE")
print("=" * 80)

parser = SASParser()
statements, inline_data = parser.parse(sas_code)

print("\nAST node types:")
for i, node in enumerate(statements):
    if isinstance(node, dict):
        print(f"{i}: {node.get('type', 'unknown')}")
    else:
        print(f"{i}: [non-dict: {type(node).__name__}] {node}")

# Filter out non-dict nodes
ast_dicts = [n for n in statements if isinstance(n, dict)]
print(f"\nTotal nodes: {len(statements)}, Dict nodes: {len(ast_dicts)}")

print("\nDict nodes (first 10):")
for i, node in enumerate(ast_dicts[:10]):
    print(f"{i}: {node}")

print("\n" + "=" * 80)
print("GENERATING R CODE")
print("=" * 80)

gen = RCodeGenerator()
try:
    r_code = gen.generate(ast_dicts, inline_data=inline_data)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nGenerated R code (lines 1-60):")
lines = r_code.split('\n')
for i, line in enumerate(lines[:60], 1):
    print(f"{i:3}: {line}")

# Look for the problematic line
print("\n" + "=" * 80)
print("CHECKING FOR PROBLEMATIC LINES")
print("=" * 80)
for i, line in enumerate(lines, 1):
    if 'haven::read_sas' in line and '/home' in line:
        print(f"Line {i}: {line}")
    if 'ae_raw' in line and 'haven::read_sas' in line and 'file.path' in line:
        print(f"Line {i}: {line}")
