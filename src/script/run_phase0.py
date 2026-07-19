# Verification script for Phase 0: Project Scaffold & Environment Setup
import os
import yaml
import sys

# Add project root to python path to resolve src imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

def main():
    print("=" * 60)
    print("RUNNING PHASE 0 VERIFICATION: Project Scaffold & Environment Setup")
    print("=" * 60)

    # 1. Test dependency resolutions
    dependencies = [
        ("groq", "groq"),
        ("pydantic", "pydantic"),
        ("pandas", "pandas"),
        ("yaml", "pyyaml"),
        ("dotenv", "python-dotenv"),
        ("bs4", "beautifulsoup4")
    ]
    
    import_errors = 0
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            print(f"[OK] Import '{module_name}' ({package_name}): SUCCESS")
        except ImportError as e:
            print(f"[ERROR] Import '{module_name}' ({package_name}): FAILED - {e}")
            import_errors += 1
            
    if import_errors > 0:
        print(f"\n[ERROR] Phase 0 failed: {import_errors} import errors detected.")
        sys.exit(1)

    # 2. Test config.yaml loading
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"[ERROR] Configuration check: FAILED - {config_path} file missing.")
        sys.exit(1)
        
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            assert config is not None
            assert "paths" in config, "Missing 'paths' config block."
            assert "llm" in config, "Missing 'llm' config block."
            print(f"[OK] Configuration check: SUCCESS (parsed {config_path} successfully)")
    except Exception as e:
        print(f"[ERROR] Configuration check: FAILED - {e}")
        sys.exit(1)

    # 3. Test environment templates
    if os.path.exists(".env") or os.path.exists(".env.template"):
        print("[OK] Environment templates check: SUCCESS (.env files detected)")
    else:
        print("[ERROR] Environment templates check: FAILED - missing both .env and .env.template")
        sys.exit(1)

    print("\n[OK] PHASE 0 VERIFICATION COMPLETED: ALL SANITY CHECKS PASSED.")
    print("=" * 60)

if __name__ == "__main__":
    main()
