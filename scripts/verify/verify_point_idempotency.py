from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

from _bootstrap import setup_project_path

setup_project_path()

from backend.common.services.memory.point_ids import stable_point_id


def main() -> int:
    expected = stable_point_id("document", 7, "content-hash", 3)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _: stable_point_id("document", 7, "content-hash", 3),
                range(100),
            )
        )
    if set(results) != {expected}:
        print("FAIL: concurrent deterministic point ID generation was inconsistent.")
        return 1
    if stable_point_id("document", 7, "content-hash", 4) == expected:
        print("FAIL: distinct chunks received the same point ID.")
        return 1
    uuid.UUID(expected)
    print("PASS: Qdrant point IDs are deterministic, distinct, valid UUIDs, and thread-safe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
