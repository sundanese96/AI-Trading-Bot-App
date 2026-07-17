import os

filepath = "/home/x/AI-Trading-Bot-App/backend/services/market.py"
with open(filepath, "r") as f:
    content = f.read()

target = '''                    current_panic = {
                        "active": False,
                        "type": "",
                        "title": "",
                        "timeLeft": 0
                    }'''
replacement = '''                    current_panic.clear()
                    current_panic.update({
                        "active": False,
                        "type": "",
                        "title": "",
                        "timeLeft": 0
                    })'''

content = content.replace(target, replacement)

with open(filepath, "w") as f:
    f.write(content)
print("Patched market.py for current_panic")
