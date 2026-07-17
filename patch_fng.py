import os
import re

filepath = "/home/x/AI-Trading-Bot-App/backend/services/market.py"
with open(filepath, "r") as f:
    content = f.read()

target1 = '''                    fng_cache = data["data"][0]'''
replacement1 = '''                    fng_cache.clear()
                    fng_cache.update(data["data"][0])'''

target2 = '''    fng_cache = {
        "value": str(new_val),
        "value_classification": classification,
        "timestamp": str(int(time.time())),
        "time_until_update": str(max(0, int(fng_cache.get("time_until_update", "24000")) - 60))
    }'''
replacement2 = '''    fng_cache.clear()
    fng_cache.update({
        "value": str(new_val),
        "value_classification": classification,
        "timestamp": str(int(time.time())),
        "time_until_update": str(max(0, int(fng_cache.get("time_until_update", "24000")) - 60))
    })'''

content = content.replace(target1, replacement1)
content = content.replace(target2, replacement2)

with open(filepath, "w") as f:
    f.write(content)
print("Patched market.py")
