#!/usr/bin/env python3
"""Test if supabase can be imported properly"""

import sys
print("Python path:")
for p in sys.path:
    print(f"- {p}")

try:
    import supabase
    print("\n✅ Supabase successfully imported!")
    print(f"Supabase version: {supabase.__version__}")
except ImportError as e:
    print(f"\n❌ Import error: {e}")

print("\nChecking if all dependencies are installed:")
modules = ["gotrue", "postgrest", "realtime", "storage3", "supafunc"]
for module in modules:
    try:
        __import__(module)
        print(f"✅ {module} - OK")
    except ImportError as e:
        print(f"❌ {module} - {e}") 