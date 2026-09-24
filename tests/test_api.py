import argparse
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient


parser = argparse.ArgumentParser(description="Run API tests for one service.")
parser.add_argument("service", choices=["device", "monitoring"])
service = parser.parse_args().service
test_database = tempfile.TemporaryDirectory(prefix="edgefleet-tests-")
database_path = Path(test_database.name) / "test.db"

# Configure an isolated database before importing the service's startup code.
os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
service_path = Path(__file__).resolve().parents[1] / f"{service}-service"
sys.path.insert(0, str(service_path))
main = importlib.import_module("main")

client = TestClient(main.app)


class ServiceTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(client.get("/health").status_code, 200)

    def test_workflow(self):
        if service == "device":
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/static/app.js").status_code, 200)
            payload = dict(
                name="Test device",
                type="sensor",
                location="lab",
                software_version="1.0",
                ip_address="127.0.0.1",
            )
            response = client.post("/devices", json=payload)
            self.assertEqual(response.status_code, 201, response.text)
            device_id = response.json()["id"]
            url = f"/devices/{device_id}"
            self.assertEqual(client.get(url).status_code, 200)
            self.assertEqual(
                client.put(url, json={"name": None}).status_code, 422
            )
            self.assertEqual(
                client.put(url, json={"name": "Updated"}).json()["name"],
                "Updated",
            )
            self.assertEqual(client.put(url, json={}).status_code, 200)
            for response, expected in [
                (httpx.Response(404), 200),
                (httpx.Response(500), 502),
                (httpx.Response(200, text="invalid"), 502),
                (httpx.Response(200, json={"status": "ONLINE"}), 200),
            ]:
                with patch("main.httpx.get", return_value=response):
                    self.assertEqual(
                        client.get(url + "/details").status_code, expected
                    )
            with patch(
                "main.httpx.get", side_effect=httpx.ConnectError("offline")
            ):
                self.assertEqual(client.get(url + "/details").status_code, 503)
            self.assertEqual(client.delete(url).status_code, 204)
            self.assertEqual(client.get(url).status_code, 404)
            self.assertEqual(
                client.post(
                    "/devices", json={**payload, "name": ""}
                ).status_code,
                422,
            )
        else:
            device_id = str(uuid4())
            url = f"/health-reports/{device_id}/latest"
            self.assertEqual(client.get(url).status_code, 404)
            payload = dict(
                device_id=device_id,
                status="ONLINE",
                cpu_usage=20,
                memory_usage=30,
            )
            self.assertEqual(
                client.post("/health-reports", json=payload).status_code, 201
            )
            self.assertEqual(client.get(url).json()["cpu_usage"], 20)
            self.assertEqual(
                client.post(
                    "/health-reports", json={**payload, "cpu_usage": 101}
                ).status_code,
                422,
            )
            self.assertEqual(
                client.post(
                    "/health-reports", json={**payload, "status": "INVALID"}
                ).status_code,
                422,
            )


if __name__ == "__main__":
    try:
        unittest.main(argv=[sys.argv[0]])
    finally:
        client.close()
        main.engine.dispose()
        test_database.cleanup()
