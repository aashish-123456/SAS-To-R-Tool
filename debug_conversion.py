#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from app.services.sas_parser import SASParser
from app.services.r_generator import RCodeGenerator

with open('backend/data/uploads/041b8338-d58c-4873-a0dc-6a0433947e15_sas_15c9c78a-bd56-401d-97d6-9d381d7d8d63_Sas1.txt', 'r') as f:
    sas_code = f.read()

statements, inline_data = SASParser().parse(sas_code)
statements = [n for n in statements if isinstance(n, dict)]

# Test _sas2r directly
gen = RCodeGenerator()
test_value = 'input(AE_STARTDT,date9.)'
converted = gen._sas2r(test_value)
print(f'Direct _sas2r test:')
print(f'  Input: {test_value}')
print(f'  Output: {converted}')
print()

# Now generate and check the full output
gen2 = RCodeGenerator()
r_code = gen2.generate(statements, inline_data=inline_data)
lines = r_code.split('\n')
for i, line in enumerate(lines[27:37], 28):
    print(f'{i:3}: {line}')
