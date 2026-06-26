#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from app.services.sas_parser import SASParser

with open('backend/data/uploads/041b8338-d58c-4873-a0dc-6a0433947e15_sas_15c9c78a-bd56-401d-97d6-9d381d7d8d63_Sas1.txt', 'r') as f:
    sas_code = f.read()

statements, inline_data = SASParser().parse(sas_code)
statements = [n for n in statements if isinstance(n, dict)]

# Find the IF statement nodes
for i, node in enumerate(statements):
    if node.get('type') == 'if_statement':
        print(f'IF statement {i}:')
        print(f'  condition: {node.get("condition")}')
        print(f'  then_clause: {node.get("then_clause")}')
        print(f'  else_clause: {node.get("else_clause")}')
        print()
