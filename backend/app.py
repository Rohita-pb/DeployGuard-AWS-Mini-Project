import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from sqlalchemy import text

from backend.config import Config
from backend.database import init_db, SessionLocal
from backend.routes.apps import apps_bp
from backend.routes.health_checks import health_bp
from backend.routes.deployments import deployments_bp
from backend.routes.incidents import incidents_bp
from backend.routes.rollbacks import rollbacks_bp
from backend.routes.reports import reports_bp


def create_app(config_class=Config):
    """Application factory for DeployGuard Flask backend."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for cross-origin frontend communication if served separately
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Database
    init_db(app.config["DATABASE_URL"])

    # Register Blueprints
    app.register_blueprint(apps_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(deployments_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(rollbacks_bp)
    app.register_blueprint(reports_bp)

    # API Root Health Endpoint
    @app.route("/api/health", methods=["GET"])
    def backend_health():
        """Health check for the DeployGuard backend application itself."""
        db_status = "UNKNOWN"
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            db_status = "CONNECTED"
        except Exception as e:
            db_status = f"ERROR: {str(e)}"

        return jsonify({
            "status": "UP",
            "service": "DeployGuard Platform",
            "version": "1.0.0",
            "database": db_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    # Serve Frontend UI directly from backend for single-command development
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    @app.route("/", methods=["GET"])
    def serve_frontend_root():
        if frontend_dir.exists():
            return send_from_directory(frontend_dir, "index.html")
        return jsonify({"message": "DeployGuard API is running. Frontend not found."}), 200

    @app.route("/<path:path>", methods=["GET"])
    def serve_frontend_assets(path):
        if (frontend_dir / path).exists():
            return send_from_directory(frontend_dir, path)
        if frontend_dir.exists() and not path.startswith("api/"):
            return send_from_directory(frontend_dir, "index.html")
        return jsonify({"success": False, "error": "Not Found"}), 404

    # Global Error Handlers (prevent stack trace leakage)
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "API route not found."}), 404
        if frontend_dir.exists():
            return send_from_directory(frontend_dir, "index.html")
        return jsonify({"success": False, "error": "Resource not found."}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "success": False,
            "error": "An internal server error occurred. Please verify logs."
        }), 500

    return app


if __name__ == "__main__":
    app = create_app()
    host = app.config.get("HOST", "127.0.0.1")
    port = app.config.get("PORT", 5000)
    print(f"============================================================")
    print(f" DeployGuard MVP running on http://{host}:{port}")
    print(f" Dashboard and API accessible at http://{host}:{port}/")
    print(f"============================================================")
    app.run(host=host, port=port, debug=True)
