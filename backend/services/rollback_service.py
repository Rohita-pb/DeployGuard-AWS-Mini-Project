from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models import Deployment, RollbackEvent, Application


class DeploymentProviderInterface:
    """
    Interface for deployment / rollback execution.
    Can be replaced in production with AWS CodeDeploy, ECS, or Kubernetes deployments.
    """
    def execute_rollback(self, app: Application, source_deployment: Deployment, target_deployment: Deployment) -> dict:
        raise NotImplementedError


class SimulatedDeploymentProvider(DeploymentProviderInterface):
    """
    Simulated rollback execution for local MVP.
    Accurately documents that this is a simulated workflow.
    """
    def execute_rollback(self, app: Application, source_deployment: Deployment, target_deployment: Deployment) -> dict:
        # For local development without active cloud pipelines, simulate successful rollback
        return {
            "status": "SIMULATED_SUCCESS",
            "message": f"Rollback simulated successfully from version {source_deployment.version} to {target_deployment.version}."
        }


# Active deployment provider (swappable with AWS CodeDeploy later)
current_deployment_provider = SimulatedDeploymentProvider()


def initiate_rollback(db: Session, source_deployment_id: int, target_deployment_id: int):
    """
    Executes a rollback workflow from source_deployment to target_deployment.
    Records the RollbackEvent and creates a new Deployment entry reflecting the rollback.
    """
    source_deployment = db.query(Deployment).filter(Deployment.id == source_deployment_id).first()
    if not source_deployment:
        raise ValueError(f"Source deployment with ID {source_deployment_id} not found.")

    target_deployment = db.query(Deployment).filter(Deployment.id == target_deployment_id).first()
    if not target_deployment:
        raise ValueError(f"Target deployment with ID {target_deployment_id} not found.")

    if source_deployment.application_id != target_deployment.application_id:
        raise ValueError("Source and target deployments must belong to the same application.")

    app = source_deployment.application

    # Execute via provider
    provider_result = current_deployment_provider.execute_rollback(app, source_deployment, target_deployment)

    # Record the rollback event
    rollback_event = RollbackEvent(
        application_id=app.id,
        source_deployment_id=source_deployment.id,
        target_deployment_id=target_deployment.id,
        status=provider_result.get("status", "SIMULATED_SUCCESS"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(rollback_event)

    # Mark source deployment status
    source_deployment.status = "ROLLED_BACK"

    # Create a new deployment record representing the rolled-back state
    new_deployment = Deployment(
        application_id=app.id,
        version=target_deployment.version,
        status="SUCCESS",
        notes=f"[SIMULATED ROLLBACK] Rolled back from version {source_deployment.version} to target version {target_deployment.version}.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_deployment)

    db.commit()
    db.refresh(rollback_event)

    return {
        "rollback_event": rollback_event.to_dict(),
        "new_deployment": new_deployment.to_dict(),
        "is_simulated": True,
        "message": provider_result.get("message"),
    }
