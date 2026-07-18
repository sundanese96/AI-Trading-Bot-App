import re

with open("src/components/AIBotPanel.tsx", "r") as f:
    content = f.read()

# find all top level returns or JSX blocks
lines = content.split('\n')
for i, line in enumerate(lines):
    if "return (" in line and i < 600:
        print(f"Return at {i}: {line.strip()}")
