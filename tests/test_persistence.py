import tempfile
from pathlib import Path
from backend.database import init_db, SessionLocal
from backend.models import Application, Deployment


def test_sqlite_persistence_across_restarts():
    """
    Verifies that data stored in SQLite file database persists
    after restarting the database engine and session factory.
    """
    temp_dir = tempfile.mkdtemp()
    db_file = Path(temp_dir) / "persistence_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    try:
        # Phase 1: Initialize DB and write records
        engine1 = init_db(db_url)
        db1 = SessionLocal()

        app = Application(
            name="Persistent Service",
            base_url="https://persist.example.com",
            health_check_url="https://persist.example.com/health",
            expected_status_code=200
        )
        db1.add(app)
        db1.commit()
        db1.refresh(app)
        app_id = app.id

        dep = Deployment(
            application_id=app_id,
            version="v1.0-persistent",
            status="SUCCESS",
            notes="Should persist across restarts"
        )
        db1.add(dep)
        db1.commit()

        SessionLocal.remove()
        engine1.dispose()

        # Phase 2: Simulate application restart by re-initializing against the same file
        engine2 = init_db(db_url)
        db2 = SessionLocal()

        persisted_app = db2.query(Application).filter(Application.id == app_id).first()
        assert persisted_app is not None, "Application should persist in database file"
        assert persisted_app.name == "Persistent Service"

        persisted_deployments = db2.query(Deployment).filter(Deployment.application_id == app_id).all()
        assert len(persisted_deployments) == 1
        assert persisted_deployments[0].version == "v1.0-persistent"

        SessionLocal.remove()
        engine2.dispose()

    finally:
        # Cleanup temp file
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception:
                pass
