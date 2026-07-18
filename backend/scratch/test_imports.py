import sys
import traceback

modules = [
    "backend.main",
    "backend.sentix_adapter",
    "backend.api.auth",
    "backend.api.market",
    "backend.api.simulation",
    "backend.api.trades",
    "backend.services.indicators",
    "backend.core.logger"
]

for mod in modules:
    try:
        __import__(mod)
        print(f"Successfully imported {mod}")
    except Exception as e:
        print(f"Failed to import {mod}:")
        traceback.print_exc()
        sys.exit(1)

print("All imports successful!")
