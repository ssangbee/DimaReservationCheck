#!/usr/bin/env python3
import pkgutil
import sys

print("Python version:", sys.version)
print("\nAvailable packages:")
for importer, modname, ispkg in pkgutil.iter_modules():
    if any(name in modname.lower() for name in ['flask', 'request', 'http', 'web', 'beautiful', 'bs4']):
        print(f"  {modname}")

# Test specific imports
modules_to_test = ['http.server', 'urllib.request', 'json', 'sqlite3']
print("\nTesting basic modules:")
for module in modules_to_test:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError:
        print(f"  ✗ {module}")
