#!/usr/bin/env python3
import re

with open(r'd:\My Documents\家庭\我的开发\ImmersiveLoudness\src\main_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

count = 0
for i, line in enumerate(lines, 1):
    code = line.split('#')[0]
    if not re.search(r'[\u4e00-\u9fff]', code):
        continue
    if re.search(r'(\.tr\(|translate\()', code):
        continue
    # skip docstrings/comments
    s = code.strip()
    if s.startswith('"""') or s.startswith("'''"):
        continue
    count += 1
    if count <= 20:
        print(f'{i}: {code.rstrip()[:100]}')

print(f'\nTotal remaining: {count}')
