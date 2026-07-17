import os

filepath = "/home/x/AI-Trading-Bot-App/backend/main.py"
with open(filepath, "r") as f:
    content = f.read()

target = '''# Persistent Session Management'''
replacement = '''@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Persistent Session Management'''

content = content.replace(target, replacement)

with open(filepath, "w") as f:
    f.write(content)
print("Patched main.py for middleware")
