"""Helper script to initialize default community categories."""

from backend.auto_init import run_auto_init


if __name__ == "__main__":
    result = run_auto_init()
    count = result.get("categories", 0) if isinstance(result, dict) else result
    print(f"Initialized {count} community categories.")
