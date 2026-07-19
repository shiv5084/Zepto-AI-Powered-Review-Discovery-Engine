# Verification script for Phase 6: Web UI Dashboard (Next.js Frontend)
import os
import sys
import subprocess

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 60)
    print("RUNNING PHASE 6 VERIFICATION: Web UI Dashboard (Next.js)")
    print("=" * 60)

    # 1. Verify frontend directory and package.json
    frontend_path = "frontend"
    if not os.path.exists(frontend_path) or not os.path.isdir(frontend_path):
        print(f"[ERROR] Frontend directory not found at '{frontend_path}'.")
        sys.exit(1)

    package_json_path = os.path.join(frontend_path, "package.json")
    if not os.path.exists(package_json_path):
        print(f"[ERROR] package.json not found at '{package_json_path}'.")
        sys.exit(1)

    print("[OK] Found frontend directory and package.json")

    # 2. Verify all 8 metric component files exist (Zepto Q-Commerce)
    components_dir = os.path.join(frontend_path, "src", "components", "dashboard")
    required_components = [
        "RepeatPurchaseDriversSection.tsx",
        "ExplorationBarriersSection.tsx",
        "DiscoveryMethodsSection.tsx",
        "HabitDriversSection.tsx",
        "InformationNeedsSection.tsx",
        "FrustrationsSection.tsx",
        "SegmentsSection.tsx",
        "UnmetNeedsSection.tsx",
        "OpportunitiesSection.tsx",
        "SentimentSummary.tsx"
    ]

    for comp in required_components:
        comp_path = os.path.join(components_dir, comp)
        if not os.path.exists(comp_path):
            print(f"[ERROR] Required component missing: '{comp_path}'")
            sys.exit(1)
        print(f"[OK] Found component: {comp}")

    # 3. Verify other key directories & files
    key_files = [
        "src/app/layout.tsx",
        "src/app/page.tsx",
        "src/app/dashboard/page.tsx",
        "src/app/pulse-note/page.tsx",
        "src/app/opportunities/page.tsx",
        "src/app/api/dashboard/route.ts",
        "src/lib/types.ts",
        "src/lib/fetchDashboard.ts",
        "src/styles/globals.css",
        "src/styles/dashboard.module.css",
        "src/styles/navbar.module.css",
        "src/styles/pulse.module.css",
        "src/components/layout/Navbar.tsx",
        "src/components/layout/Sidebar.tsx",
        "src/components/charts/RatingBar.tsx",
        "src/components/charts/FrequencyBadge.tsx",
        "src/components/pulse/PulseNoteViewer.tsx"
    ]

    for kf in key_files:
        kf_path = os.path.join(frontend_path, kf)
        if not os.path.exists(kf_path):
            print(f"[ERROR] Key file missing: '{kf_path}'")
            sys.exit(1)
        print(f"[OK] Found key file: {kf}")

    # 4. Verify dashboard_data.json exists in root data directory
    data_path = os.path.join("data", "dashboard_data.json")
    if not os.path.exists(data_path):
        print(f"[ERROR] Dashboard data JSON file missing at '{data_path}'")
        sys.exit(1)
    print(f"[OK] Found dashboard data file at: {data_path}")

    # 5. Run next build to ensure zero compilation or typescript errors
    print("\n[ ] Running 'npm run build' inside frontend/ directory...")
    
    try:
        process = subprocess.run(
            "npm run build",
            cwd=frontend_path,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            print("[ERROR] 'npm run build' failed with TypeScript or compilation errors:")
            print(process.stdout)
            print(process.stderr)
            sys.exit(process.returncode)
            
        print("[OK] 'npm run build' completed successfully with 0 TypeScript/compilation errors.")
    except Exception as e:
        print(f"[ERROR] Failed to run 'npm run build': {e}")
        sys.exit(1)

    print("\n[OK] PHASE 6 VERIFICATION COMPLETED: ALL TASKS VERIFIED SUCCESSFULLY.")
    print("=" * 60)

if __name__ == "__main__":
    main()
