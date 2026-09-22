# EdgeFleet

EdgeFleet contains a FastAPI device service (port 8000), a FastAPI monitoring
service (port 8001), and PostgreSQL 16. The device service serves the dashboard
and retrieves the latest device health report from the monitoring service over HTTP.
Each service owns its SQLAlchemy models; both use the configured PostgreSQL database.

## Local setup

Use Python 3.10 or a compatible newer version. Create a virtual environment in
each service directory and install that directory's requirements.txt with pip.
Start PostgreSQL and create the database and user before starting the services.
In each service terminal, set DATABASE_URL to your PostgreSQL connection URL:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://USER:URL_ENCODED_PASSWORD@localhost:5432/edgefleet'
```

Replace the placeholders with local credentials. The application does not load
.env files automatically. Missing DATABASE_URL stops startup instead of silently
using a built-in password. Tables are created on service startup; this is not a
schema migration system.

From monitoring-service, run `python -m uvicorn main:app --port 8001`.
From device-service, run `python -m uvicorn main:app --port 8000`.
MONITORING_SERVICE_URL defaults to http://127.0.0.1:8001 for local development.
Open http://localhost:8000 for the dashboard and /docs on either service for its API.

## Docker and Kubernetes

Build each image from its service directory. Supply DATABASE_URL at runtime;
set MONITORING_SERVICE_URL to an address reachable from the device container.
Containers run as an unprivileged user.

The Kubernetes manifests reference existing registry image tags. Local source
edits do not update those images: build images with new tags, make them available
to your cluster, and update the two deployment image fields before deployment.

For a new setup, copy kubernetes/postgres-secret.example.yaml to
kubernetes/postgres-secret.yaml and replace both password placeholders, using
URL encoding in DATABASE_URL. The local secret file is ignored by Git. Do not
overwrite an existing local secret when following this setup.
Apply the local secret first, then the PVC, PostgreSQL deployment and service,
then the two application deployments and services. Apply each intended file
explicitly; do not apply the entire kubernetes directory, which includes the
placeholder example.

Use `kubectl port-forward service/device-service 8000:8000` to access the dashboard.
The application /health probes check process responsiveness, not database or
downstream availability. PostgreSQL uses Recreate to avoid overlapping database
pods sharing one data directory during deployment updates.

## API behavior

- Device service: POST/GET /devices, GET/PUT/DELETE /devices/{id}, and
  GET /devices/{id}/details. PUT updates supplied fields only; explicit null
  values are rejected because device columns are required.
- Monitoring service: POST /health-reports and GET /health-reports/{device_id}/latest.
- No report produces null health in device details. A connection failure produces
  503; unexpected upstream status or invalid JSON produces 502.
- Both services expose GET /health.

## Scope and submission

This is a demonstration application without authentication. Health reports are
associated by device UUID; the monitoring service does not enforce existence in
the device service, and deleting a device does not delete its reports. Startup
table creation is retained; provision tables before testing concurrent first
startup of multiple replicas. Resource sizing and database backups need workload
and operational decisions.

Submit source files and the secret example, excluding virtual environments,
local secrets, caches, and local working files. Git ignore rules do not exclude files
from a manually created ZIP. The current local password existed in the original
source; removing defaults and ignoring the secret does not rotate it.
Follow the course requirements for declaring AI assistance.
