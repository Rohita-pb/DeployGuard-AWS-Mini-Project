from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

Base = declarative_base()

# Scoped session that can be reconfigured with new engines
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False))
_engine = None


def init_db(database_url: str):
    """
    Initializes or reconfigures the database engine and session factory.
    Creates tables if they do not exist.
    """
    global _engine

    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,
    }

    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool

    _engine = create_engine(database_url, **engine_kwargs)
    SessionLocal.configure(bind=_engine)

    # Import models to register with Base before create_all
    import backend.models  # noqa: F401
    Base.metadata.create_all(bind=_engine)
    return _engine


def get_engine():
    """Returns the currently active engine."""
    return _engine


def get_db():
    """Yields a database session and ensures closure after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
