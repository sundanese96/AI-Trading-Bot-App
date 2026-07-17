import os

filepath = "/home/x/AI-Trading-Bot-App/backend/services/market.py"
with open(filepath, "r") as f:
    content = f.read()

target = '''            assets = new_assets'''
replacement = '''            assets.clear()
            assets.extend(new_assets)'''

content = content.replace(target, replacement)

with open(filepath, "w") as f:
    f.write(content)
print("Patched market.py for assets")
