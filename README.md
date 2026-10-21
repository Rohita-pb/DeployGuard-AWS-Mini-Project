# DeployGuard — Deployment Failure Detection and Rollback Monitoring Platform

DeployGuard is a full-stack deployment monitoring platform designed for cloud engineering teams. It allows developers to register applications, execute security-hardened health checks, track deployment versions, automatically detect failures, deduplicate active incidents, maintain an audit history, and trigger simulated rollback workflows.

Built as a lightweight, modular MVP for a **Cloud Computing Mini-Project**, DeployGuard is fully functional locally with **Flask + SQLite** and structured with clean service boundaries for seamless future migration to **Amazon Web Services (EC2, VPC, RDS MySQL, S3, SQS, SNS)**.

---

## 1. Architecture Overview

### Local MVP Architecture (Current)
- **Frontend**: Pure Vanilla HTML5, CSS3, and JavaScript (Fetch API). No frontend frameworks, zero build step.
- **Backend**: Python 3.13, Flask, SQLAlchemy 2.0 ORM, PyMySQL.
- **Local Database**: SQLite (`deployguard.db`) with automatic table creation and thread-safe connection pooling.
- **Security Engine**: SSRF prevention guard blocking localhost, loopback, private RFC-1918 subnets, and AWS EC2 IMDS metadata IP (`169.254.169.254`).
- **Modular Services**: Decoupled modules for Health Checking, Incident Management, Simulated Rollback, Storage, Notifications, and Queues.

### Target Production AWS Architecture (Roadmap)
```
  [ Users / DevOps ]
           │
           ▼
    [ Amazon Route 53 & ALB ]
           │
    [ Custom Amazon VPC (Public / Private Subnets) ]
           │
           ├──▶ [ Amazon EC2 (Flask Application & Gunicorn) ]
           │          │
           │          ├──▶ [ Amazon RDS MySQL (Database) ]
           │          ├──▶ [ Amazon S3 (CSV Reports & Artifacts) ]
           │          ├──▶ [ Amazon SNS (Email / SMS Incident Alerts) ]
           │          └──▶ [ Amazon SQS (Health Check Queue) ]
           │
           └──▶ [ AWS CloudWatch & AWS Budgets (Logs, Alarms & Costs) ]
```

---

## 2. Directory Structure

```text
Aws Mini Project/
├── run.py                     # Root launcher script (python run.py)
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules for Python & SQLite
├── README.md                  # Comprehensive documentation
├── backend/
│   ├── app.py                 # Flask app factory, static router & error handlers
│   ├── config.py              # Configuration loading (.env & defaults)
│   ├── database.py            # SQLAlchemy engine, scoped sessions & tables init
│   ├── models.py              # Application, HealthCheck, Deployment, Incident, RollbackEvent
│   ├── requirements.txt       # Python package dependencies
│   ├── routes/
│   │   ├── __init__.py        # Blueprint aggregator
│   │   ├── apps.py            # /api/apps, /api/dashboard
│   │   ├── health_checks.py   # /api/apps/<id>/check, /api/checks
│   │   ├── deployments.py     # /api/deployments
│   │   ├── incidents.py       # /api/incidents, /api/incidents/<id>/resolve
│   │   ├── rollbacks.py       # /api/rollbacks, /api/deployments/<id>/rollback
│   │   └── reports.py         # /api/reports/incidents.csv
│   └── services/
│       ├── __init__.py
│       ├── health_checker.py  # HTTP probe + SSRF defense + timeout protection
│       ├── incident_service.py# Failure evaluation & consecutive deduplication
│       ├── rollback_service.py# Modular rollback interface (simulated provider)
│       ├── report_service.py  # CSV report builder
│       ├── storage_service.py # Local disk provider / ready-to-plug S3 provider
│       ├── notification_service.py # Console provider / ready-to-plug SNS provider
│       └── queue_service.py   # Direct in-process / ready-to-plug SQS provider
├── frontend/
│   ├── index.html             # Responsive dashboard, modals, and views
│   ├── style.css              # Modern Vanilla CSS design system
│   └── app.js                 # API interactions, DOM manipulation, state management
└── tests/
    ├── conftest.py            # Pytest test client and in-memory DB fixture
    ├── test_health.py         # Backend health endpoint test
    ├── test_apps.py           # Application CRUD and validation tests
    ├── test_health_checks.py  # Probes and SSRF security tests
    ├── test_incidents.py      # Failure detection & deduplication tests
    ├── test_deployments.py    # Deployment tracking tests
    ├── test_rollbacks.py      # Rollback workflow tests
    ├── test_reports.py        # CSV export tests
    ├── test_persistence.py    # SQLite engine restart persistence test
    └── test_live.py           # End-to-end HTTP integration test against live server
```

---

## 3. Quick Start — Windows PowerShell Setup

Follow these exact commands in **Windows PowerShell** to run the project.

### Step 1: Open PowerShell and Navigate to Workspace
```powershell
cd "c:\Users\Admin\Desktop\Aws Mini Project"
```

### Step 2: (Optional) Create & Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
pip install -r backend\requirements.txt
```

### Step 4: Configure Environment Variables
Copy the template configuration file:
```powershell
Copy-Item .env.example .env
```
*(By default, `.env` is configured to use local SQLite, so no manual editing is needed for local testing!)*

### Step 5: Start the Server
Launch the application using either `run.py` or `python backend\app.py`:
```powershell
python run.py
```

Output:
```text
============================================================
 DeployGuard MVP Platform
 Web UI & Dashboard: http://127.0.0.1:5000/
 API Health Check:   http://127.0.0.1:5000/api/health
============================================================
 * Running on http://127.0.0.1:5000
```

### Step 6: Access the Application
Open your web browser and navigate to:
```text
http://127.0.0.1:5000/
```
The Flask backend automatically serves both the API and the Vanilla JavaScript frontend from the same port.

---

## 4. API Documentation

All API responses follow a consistent JSON structure.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Backend status and database connectivity check |
| `GET` | `/api/dashboard` | Dashboard metrics (total, healthy, unhealthy, incidents) |
| `GET` | `/api/apps` | List all registered applications with latest status |
| `POST` | `/api/apps` | Register a new application with validation |
| `GET` | `/api/apps/<id>` | Retrieve single application details with history |
| `DELETE` | `/api/apps/<id>` | Delete application and cascade delete all records |
| `POST` | `/api/apps/<id>/check` | Trigger manual health check & incident evaluation |
| `GET` | `/api/apps/<id>/checks` | Retrieve health checks for an application |
| `GET` | `/api/checks` | Retrieve recent health checks across all applications |
| `GET` | `/api/deployments` | List all recorded deployments (newest first) |
| `POST` | `/api/deployments` | Record a deployment event manually |
| `GET` | `/api/incidents` | List incidents (filter by `?status=OPEN` or `RESOLVED`) |
| `PATCH` | `/api/incidents/<id>/resolve` | Resolve an active incident |
| `GET` | `/api/rollbacks` | List rollback event history |
| `POST` | `/api/deployments/<id>/rollback` | Initiate simulated rollback to target deployment |
| `GET` | `/api/reports/incidents.csv` | Download incidents report as CSV |

---

### Example API Requests & Responses

#### 1. Register Application
**Request:**
`POST /api/apps`
```json
{
  "name": "Payments API",
  "base_url": "https://httpbin.org",
  "health_check_url": "https://httpbin.org/status/200",
  "expected_status_code": 200
}
```
**Response (201 Created):**
```json
{
  "success": true,
  "message": "Application registered successfully.",
  "data": {
    "id": 1,
    "name": "Payments API",
    "base_url": "https://httpbin.org",
    "health_check_url": "https://httpbin.org/status/200",
    "expected_status_code": 200,
    "current_status": "UNKNOWN",
    "last_response_time_ms": null,
    "created_at": "2026-10-21T04:23:29.448098"
  }
}
```

#### 2. Run Health Check
**Request:**
`POST /api/apps/1/check`
**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "check": {
      "id": 1,
      "application_id": 1,
      "application_name": "Payments API",
      "status": "HEALTHY",
      "http_status_code": 200,
      "response_time_ms": 142.35,
      "error_message": null,
      "checked_at": "2026-10-21T04:25:01.120300"
    },
    "incident": null,
    "is_incident_created": false
  }
}
```

#### 3. Initiate Simulated Rollback
**Request:**
`POST /api/deployments/2/rollback`
```json
{
  "target_deployment_id": 1
}
```
**Response (200 OK):**
```json
{
  "success": true,
  "message": "Rollback simulated successfully from version v1.1.0 to v1.0.0.",
  "is_simulated": true,
  "data": {
    "id": 1,
    "application_id": 1,
    "source_deployment_id": 2,
    "source_version": "v1.1.0",
    "target_deployment_id": 1,
    "target_version": "v1.0.0",
    "status": "SIMULATED_SUCCESS",
    "created_at": "2026-10-21T04:28:12.391200"
  },
  "new_deployment": {
    "id": 3,
    "application_id": 1,
    "version": "v1.0.0",
    "status": "SUCCESS",
    "notes": "[SIMULATED ROLLBACK] Rolled back from version v1.1.0 to target version v1.0.0."
  }
}
```

---

## 5. Security Measures (SSRF Defense & Resilience)

DeployGuard implements strict security validation on target URLs:
1. **Scheme Whitelisting**: Only `http` and `https` protocols are allowed.
2. **Localhost & Loopback Blocking**: Hostnames such as `localhost`, `127.0.0.1`, `::1`, and `0.0.0.0` are blocked.
3. **DNS Resolution & Private IP Guard**: Target hostnames are resolved via DNS, and resolved IPs are verified against RFC-1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) and link-local ranges (`169.254.0.0/16`).
4. **AWS Metadata Protection**: Explicitly blocks requests targeting `169.254.169.254` (AWS EC2 Instance Metadata Service).
5. **Redirect Bypass Protection**: Redirects are disabled on probes (`allow_redirects=False`) to avoid redirect hopping into internal networks.
6. **Timeouts & Memory Limits**: 5-second socket timeout and max 1MB response stream limit to prevent denial-of-service memory exhaustion.

---

## 6. Testing Instructions & Results

DeployGuard includes a test suite covering unit, functional, security, and persistence tests.

### Running Automated Tests
Run pytest in Windows PowerShell:
```powershell
python -m pytest -v
```

### Test Coverage Summary:
- `tests/test_health.py`: Backend health status and DB probe.
- `tests/test_apps.py`: Application registration, listing, deletion, duplicate prevention, input validation.
- `tests/test_health_checks.py`: Probes, expected vs unexpected HTTP statuses, timeouts, and SSRF security defense.
- `tests/test_incidents.py`: Incident creation, deduplication of consecutive failures, and resolution.
- `tests/test_deployments.py`: Deployment event recording and ordering.
- `tests/test_rollbacks.py`: Simulated rollback audit logging and status cascading.
- `tests/test_reports.py`: CSV report structure, column headers, and MIME type.
- `tests/test_persistence.py`: SQLite engine restart data persistence.

**Test Results:**
```text
======================== 17 passed in 0.71s ========================
```

---

## 7. Features Implemented vs. Pending

### Implemented (MVP)
- [x] Full-Stack Dashboard with live real-time metrics.
- [x] Application management (Register, List, View, Delete with modal confirmation).
- [x] Security-hardened health check probe system with SSRF protection.
- [x] Automated failure detection and incident creation.
- [x] Consecutive failure deduplication (reuses single open incident until resolved).
- [x] Incident resolution workflow.
- [x] Deployment history recording (version, status, notes).
- [x] Rollback workflow with clear simulation labeling.
- [x] Global health check history log with latency and status codes.
- [x] Incident report CSV generation and download.
- [x] Single-command running (Flask serves API + Vanilla JS/CSS frontend).
- [x] Plug-and-play modular interfaces for AWS S3, SNS, and SQS.
- [x] SQLite persistence and PyMySQL driver support for RDS.

### Pending (Future Post-MVP Iterations)
- [ ] User authentication and role-based access control (RBAC).
- [ ] Automated scheduled background cron probes via Celery or AWS Lambda.
- [ ] Live AWS CodeDeploy / ECS deployment rollback API integration.
- [ ] Multi-region health check probe nodes.

---

## 8. AWS Deployment Roadmap (Cloud Computing Project)

To transition DeployGuard from local SQLite to AWS production for your mini-project presentation, follow these architectural steps:

### Phase 1: Amazon RDS MySQL Database Setup
1. Create a MySQL DB instance in Amazon RDS (Free Tier `db.t3.micro` or `db.t4g.micro`).
2. Place the RDS instance in private subnets within your custom VPC.
3. Update the `.env` configuration on your EC2 instance:
   ```env
   DATABASE_URL=mysql+pymysql://<db_user>:<db_password>@<rds-endpoint>:3306/deployguard
   ```
   *No backend code changes are required because SQLAlchemy and PyMySQL are already integrated.*

### Phase 2: Amazon EC2 Application Server
1. Launch an Amazon EC2 instance (Ubuntu 24.04 or Amazon Linux 2023, `t2.micro` or `t3.micro`).
2. Attach an IAM Role with least-privilege policies for S3, SNS, and CloudWatch.
3. Install Python 3 and clone the repository.
4. Run with Gunicorn and Nginx reverse proxy:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 127.0.0.1:5000 "backend.app:create_app()"
   ```

### Phase 3: Amazon S3 Report Storage Integration
1. Create an S3 Bucket (e.g. `deployguard-incident-reports`).
2. In `.env`, switch storage provider:
   ```env
   STORAGE_PROVIDER=s3
   S3_BUCKET_NAME=deployguard-incident-reports
   AWS_REGION=us-east-1
   ```
   *DeployGuard's `backend/services/storage_service.py` will automatically stream generated CSV reports to S3 using `boto3`.*

### Phase 4: Amazon SNS Incident Notifications
1. Create an SNS Topic (e.g. `deployguard-alerts`) and subscribe your email/phone.
2. In `.env`, switch notification provider:
   ```env
   NOTIFICATION_PROVIDER=sns
   SNS_TOPIC_ARN=arn:aws:sns:us-east-1:<account-id>:deployguard-alerts
   ```
   *DeployGuard's `backend/services/notification_service.py` will publish alerts to SNS whenever an incident is opened.*

### Phase 5: Amazon CloudWatch & AWS Budgets
1. Stream application logs (`/var/log/nginx/` and Flask logs) to CloudWatch Logs using AWS CloudWatch Agent.
2. Create CloudWatch Alarms for CPU utilization > 80% and 5xx HTTP response spikes.
3. Configure an AWS Budget alert ($5.00 limit) to avoid unexpected cloud charges.
