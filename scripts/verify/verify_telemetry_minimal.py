import sys
from pathlib import Path

from sqlmodel import Session

root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.append(str(root))

from backend.common.database import create_db_and_tables, get_engine
from backend.common.models.sql import DerivedMemory, EventRaw, FilesIndex, FolderConsent


def main() -> None:
    create_db_and_tables()
    with Session(get_engine()) as session:
        event = EventRaw(
            event_type="test_event",
            session_id="test_session",
            payload_json="{}",
            hash="deadbeef",
            source="test",
        )
        session.add(event)
        session.commit()

        memory = DerivedMemory(
            memory_type="test_memory",
            source_refs="{}",
            summary_text="summary",
            qdrant_point_id="point",
        )
        session.add(memory)
        session.commit()

        if session.get(FolderConsent, "C:/tmp/test") is None:
            consent = FolderConsent(path="C:/tmp/test")
            session.add(consent)
            session.commit()

        if session.get(FilesIndex, "C:/tmp/file.txt") is None:
            file_entry = FilesIndex(path="C:/tmp/file.txt", content_hash="hash", mtime=0.0)
            session.add(file_entry)
            session.commit()

    print("Telemetry minimal verification OK.")


if __name__ == "__main__":
    main()
