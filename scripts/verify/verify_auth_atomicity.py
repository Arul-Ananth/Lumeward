from _bootstrap import setup_project_path

setup_project_path()

from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.common.models.sql import AuthIdentity, User
from backend.common.services.auth.store import create_user_with_password_identity


def main() -> int:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def fail_identity_insert(session, _flush_context, _instances) -> None:
        if any(isinstance(value, AuthIdentity) for value in session.new):
            raise RuntimeError("simulated identity failure")

    with Session(engine) as session:
        event.listen(session, "before_flush", fail_identity_insert)
        try:
            create_user_with_password_identity(
                session,
                full_name="Atomic Test",
                email="atomic@example.com",
                password="test-password",
            )
        except RuntimeError as exc:
            if str(exc) != "simulated identity failure":
                raise
        else:
            raise AssertionError("simulated identity failure was not raised")
        finally:
            event.remove(session, "before_flush", fail_identity_insert)

        if session.exec(select(User).where(User.email == "atomic@example.com")).first() is not None:
            raise AssertionError("user persisted after identity creation failed")

        user, identity = create_user_with_password_identity(
            session,
            full_name="Atomic Test",
            email="atomic@example.com",
            password="test-password",
        )
        if user.id is None or identity.id is None or identity.user_id != user.id:
            raise AssertionError("user and identity were not committed together")

    print("PASS: password user and identity creation is atomic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
