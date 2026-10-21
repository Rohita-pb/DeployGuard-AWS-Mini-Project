from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    base_url = Column(String(255), nullable=False)
    health_check_url = Column(String(255), nullable=False)
    expected_status_code = Column(Integer, nullable=False, default=200)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    # Relationships
    health_checks = relationship(
        "HealthCheck",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(HealthCheck.checked_at)"
    )
    deployments = relationship(
        "Deployment",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(Deployment.created_at)"
    )
    incidents = relationship(
        "Incident",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(Incident.opened_at)"
    )
    rollbacks = relationship(
        "RollbackEvent",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(RollbackEvent.created_at)"
    )

    def to_dict(self, include_latest_check=True):
        data = {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "health_check_url": self.health_check_url,
            "expected_status_code": self.expected_status_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_latest_check:
            latest = self.health_checks[0] if self.health_checks else None
            data["latest_check"] = latest.to_dict() if latest else None
            # Also calculate current status
            if latest:
                data["current_status"] = latest.status
                data["last_response_time_ms"] = latest.response_time_ms
            else:
                data["current_status"] = "UNKNOWN"
                data["last_response_time_ms"] = None
        return data


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False)  # 'HEALTHY' | 'UNHEALTHY'
    http_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, nullable=False, default=utcnow)

    application = relationship("Application", back_populates="health_checks")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "application_name": self.application.name if self.application else None,
            "status": self.status,
            "http_status_code": self.http_status_code,
            "response_time_ms": round(self.response_time_ms, 2) if self.response_time_ms is not None else None,
            "error_message": self.error_message,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="SUCCESS")  # 'SUCCESS', 'FAILED', 'PENDING', 'ROLLED_BACK'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    application = relationship("Application", back_populates="deployments")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "application_name": self.application.name if self.application else None,
            "version": self.version,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="OPEN")  # 'OPEN' | 'RESOLVED'
    opened_at = Column(DateTime, nullable=False, default=utcnow)
    resolved_at = Column(DateTime, nullable=True)

    application = relationship("Application", back_populates="incidents")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "application_name": self.application.name if self.application else None,
            "reason": self.reason,
            "status": self.status,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class RollbackEvent(Base):
    __tablename__ = "rollback_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    source_deployment_id = Column(Integer, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    target_deployment_id = Column(Integer, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(30), nullable=False, default="SIMULATED_SUCCESS")  # 'SIMULATED_SUCCESS', 'FAILED'
    created_at = Column(DateTime, nullable=False, default=utcnow)

    application = relationship("Application", back_populates="rollbacks")
    source_deployment = relationship("Deployment", foreign_keys=[source_deployment_id])
    target_deployment = relationship("Deployment", foreign_keys=[target_deployment_id])

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "application_name": self.application.name if self.application else None,
            "source_deployment_id": self.source_deployment_id,
            "source_version": self.source_deployment.version if self.source_deployment else None,
            "target_deployment_id": self.target_deployment_id,
            "target_version": self.target_deployment.version if self.target_deployment else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
