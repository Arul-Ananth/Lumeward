import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    scripts = sorted(p for p in root.glob("*.py") if p.name != "run_all.py" and not p.name.startswith("_"))

    results: list[tuple[str, int]] = []
    for script in scripts:
        print(f"--- Running {script.name} ---")
        proc = subprocess.run([sys.executable, str(script)], check=False)
        results.append((script.name, proc.returncode))

    failed = [(name, code) for name, code in results if code != 0]
    print("\n--- Verification Summary ---")
    for name, code in results:
        status = "OK" if code == 0 else f"FAILED ({code})"
        print(f"{name}: {status}")

    if failed:
        print(f"\nFailures: {len(failed)}")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
