# EdgeFleet

EdgeFleet manages edge devices and records their health reports. It includes a
browser dashboard, two FastAPI services, and a PostgreSQL database.

| Component | Purpose | Port |
| --- | --- | --- |
| Device service | Device registration, updates, deletion, and dashboard | 8000 |
| Monitoring service | Health reports and latest readings for each device | 8001 |
| PostgreSQL | Stores devices and health reports | 5432 |

The device service calls the monitoring service over HTTP to display the latest
status, CPU usage, and memory usage for each device.

## Running locally

The project uses Python 3.10 and PostgreSQL 16. Before starting the services,
create a PostgreSQL database and a user with permission to create tables in it.

Open a separate PowerShell terminal for each service. In the service directory,
create a virtual environment and install its dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set the database connection in both terminals, replacing the placeholders:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://USER:URL_ENCODED_PASSWORD@localhost:5432/edgefleet'
```

Passwords containing special characters must be URL-encoded in this connection
string. DATABASE_URL is required. Environment files are not loaded automatically.
Both services create their tables when they start.

In the monitoring-service terminal, run:

```powershell
python -m uvicorn main:app --port 8001
```

In the device-service terminal, run:

```powershell
$env:MONITORING_SERVICE_URL = 'http://127.0.0.1:8001'
python -m uvicorn main:app --port 8000
```

Open [the dashboard](http://localhost:8000). Interactive API documentation is
available at [device API docs](http://localhost:8000/docs) and
[monitoring API docs](http://localhost:8001/docs).

## Docker

Build the images from the repository root:

```powershell
docker build -t edgefleet-device-service:local ./device-service
docker build -t edgefleet-monitoring-service:local ./monitoring-service
```

Supply DATABASE_URL to each container at runtime. Set MONITORING_SERVICE_URL on
the device container to the monitoring container's address. Containers on the
same Docker network can use container names as hostnames. Inside a container,
localhost refers to that container, not the host computer or another service.
Both application images run as an unprivileged user.

## Kubernetes

The kubernetes directory contains deployments, services, a PostgreSQL volume
claim, and a secret template. The application deployments use registry images;
building a local image does not update a running deployment.

For a new installation, copy postgres-secret.example.yaml to postgres-secret.yaml
inside the kubernetes directory. Replace the password placeholders, including
the URL-encoded password in DATABASE_URL. Keep the local secret file out of Git.
Reuse an existing secret file if the database is already configured.

Apply the files individually so the placeholder secret example is not applied:

```powershell
kubectl apply -f kubernetes/postgres-secret.yaml
kubectl apply -f kubernetes/postgres-pvc.yaml
kubectl apply -f kubernetes/postgres-service.yaml
kubectl apply -f kubernetes/postgres-deployment.yaml
kubectl rollout status deployment/postgres
kubectl apply -f kubernetes/monitoring-service.yaml
kubectl apply -f kubernetes/monitoring-deployment.yaml
kubectl apply -f kubernetes/device-service.yaml
kubectl apply -f kubernetes/device-deployment.yaml
kubectl rollout status deployment/monitoring-service
kubectl rollout status deployment/device-service
```

To access the dashboard:

```powershell
kubectl port-forward service/device-service 8000:8000
```

Use a different local port, such as 18000:8000, if port 8000 is already in use.
The application probes use /health to check service responsiveness; they do not
check database or downstream service availability. PostgreSQL uses the Recreate
strategy to avoid overlapping database pods sharing the same data directory.

## API

| Service | Method and path | Purpose |
| --- | --- | --- |
| Device | POST /devices | Register a device |
| Device | GET /devices | List devices |
| Device | GET /devices/{id} | Retrieve a device |
| Device | PUT /devices/{id} | Update supplied device fields |
| Device | DELETE /devices/{id} | Delete a device |
| Device | GET /devices/{id}/details | Retrieve a device and its latest health report |
| Monitoring | POST /health-reports | Record a health report |
| Monitoring | GET /health-reports/{device_id}/latest | Retrieve the latest report |
| Both | GET /health | Check service responsiveness |

Device updates reject null values for required fields. Device details return
null health when no report exists, 503 when monitoring cannot be reached, and
502 for an unexpected upstream status or invalid JSON.

## Tests

The API tests cover device operations, input validation, health reports, and
monitoring error responses. They use a temporary SQLite database and mock
outbound monitoring requests. They do not require running services and do not
replace integration testing with PostgreSQL and real service-to-service calls.

From the repository root, use the device service's virtual environment, which
includes the HTTP client required by the test runner:

```powershell
.\device-service\.venv\Scripts\python.exe tests/test_api.py device
.\device-service\.venv\Scripts\python.exe tests/test_api.py monitoring
```

## Limitations

The application has no authentication. Monitoring associates reports with device
UUIDs without checking that the device exists. Deleting a device leaves its
health reports in the database.

Startup table creation does not manage schema migrations. For a fresh database,
create the tables with one replica of each service before scaling. Database
backups and workload-specific resource limits are not configured in this project.
