"""Isolated local containers: TLS S3, PostgreSQL, two hosts and eight workers."""

import argparse
import ipaddress
import json
import os
import statistics
import subprocess
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from simweave import maintenance
from simweave.api import create_app
from simweave.artifacts import S3
from simweave.config import Settings
from simweave.postgres import Database, Jobs, SharedArtifacts
from simweave.store import Capacity
from simweave.suites import Suite

PG = "postgres@sha256:41fc5342eefba6cc2ccda736aaf034bbbb7c3df0fdb81516eba1ba33f360162c"
S3_IMAGE = "rustfs/rustfs@sha256:8cc9801755448b71a786705ce76692c77e14936cccd87cf2fc31842e58f4d1ff"
TLS = "nginx@sha256:30f1c0d78e0ad60901648be663a710bdadf19e4c10ac6782c235200619158284"


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError("fixture container command failed: " + args[0])
    return result.stdout.strip()


def certificates(root):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "simweave-fixture")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("s3"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private, hashes.SHA256())
    )
    (root / "ca.crt").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (root / "server.key").write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1000)
    parser.add_argument("--image", default="simweave-sw013-worker")
    args = parser.parse_args()
    if not 16 <= args.jobs <= 1000:
        raise ValueError("job count must be 16..1000")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    certificates(root)
    prefix = "sw013-" + uuid.uuid4().hex[:8]
    names = []
    database = None

    def start(suffix, *options):
        name = prefix + "-" + suffix
        docker("run", "-d", "--name", name, "--network", prefix, *options)
        names.append(name)
        return name

    docker("network", "create", prefix)
    try:
        pg = start(
            "db",
            "--network-alias",
            "db",
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_PASSWORD=synthetic-postgres-only",
            "-e",
            "POSTGRES_DB=simweave",
            PG,
        )
        start(
            "objects",
            "--network-alias",
            "objects",
            "-e",
            "RUSTFS_ACCESS_KEY=synthetic-access",
            "-e",
            "RUSTFS_SECRET_KEY=synthetic-secret-only",
            S3_IMAGE,
            "/data",
        )
        (root / "nginx.conf").write_text(
            "events {}\nhttp { server { listen 443 ssl; ssl_certificate "
            "/fixture/ca.crt; ssl_certificate_key /fixture/server.key; "
            "client_max_body_size 128m; location / { proxy_pass "
            "http://objects:9000; proxy_set_header Host $http_host; "
            "proxy_request_buffering off; } } }"
        )
        tls = start(
            "s3",
            "--network-alias",
            "s3",
            "-p",
            "127.0.0.1::443",
            "--mount",
            f"type=bind,source={root},target=/fixture,readonly",
            "--mount",
            f"type=bind,source={root / 'nginx.conf'},target=/etc/nginx/nginx.conf,readonly",
            TLS,
        )
        pg_port = docker("port", pg, "5432/tcp").rsplit(":", 1)[1]
        s3_port = docker("port", tls, "443/tcp").rsplit(":", 1)[1]
        os.environ["SIMWEAVE_POSTGRES_DSN"] = (
            f"postgresql://postgres:synthetic-postgres-only@127.0.0.1:{pg_port}/simweave"
        )
        deadline = time.monotonic() + 60
        while True:
            try:
                database = Database(root / "scratch", initialize=True)
                break
            except RuntimeError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.5)
        jobs = Jobs(database)
        backend = S3(
            endpoint=f"https://127.0.0.1:{s3_port}",
            bucket="simweave-fixture",
            region="us-east-1",
            access_key="synthetic-access",
            secret="synthetic-secret-only",
            ca_bundle=str(root / "ca.crt"),
        )
        while True:
            try:
                backend.client.create_bucket(Bucket="simweave-fixture")
                break
            except Exception:
                if time.monotonic() > deadline:
                    raise RuntimeError("S3 fixture unavailable") from None
                time.sleep(0.5)
        artifacts = SharedArtifacts(database, backend)
        (root / "storage.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "endpoint": "https://s3",
                    "bucket": "simweave-fixture",
                    "ca_bundle": "/fixture/ca.crt",
                }
            )
        )
        for i in range(args.jobs):
            suite = Suite.model_validate(
                {
                    "name": f"cluster-{i}",
                    "scenarios": [{"world": {"steps": 5}}],
                    "seeds": [1],
                    "adapters": ["reference"],
                    "baseline": {},
                    "candidate": {},
                }
            )
            jobs.submit("alpha" if i % 2 else "beta", suite, str(i))
        if args.jobs == 1000:
            try:
                jobs.submit("extra", suite, "over-capacity")
                raise AssertionError("quota accepted")
            except Capacity:
                pass
        print(json.dumps({"stage": "queued", "jobs": args.jobs}), flush=True)

        def worker(suffix, hold=False):
            return start(
                suffix,
                "--mount",
                f"type=bind,source={root},target=/fixture,readonly",
                "-e",
                "SIMWEAVE_POSTGRES_DSN=postgresql://postgres:synthetic-postgres-only@db/simweave",
                "-e",
                "SIMWEAVE_S3_ACCESS_KEY=synthetic-access",
                "-e",
                "SIMWEAVE_S3_SECRET_KEY=synthetic-secret-only",
                "-e",
                "FIXTURE_HOST=" + suffix,
                "-e",
                "FIXTURE_HOLD=" + str(hold).lower(),
                args.image,
            )

        victim = worker("victim", True)
        deadline = time.monotonic() + 45
        while jobs.metrics(artifacts)["metrics"]["simweave_suite_jobs_running"] < 4:
            if time.monotonic() > deadline:
                raise RuntimeError("workers failed to claim")
            time.sleep(0.1)
        with database.connection() as db:
            stale = list(
                db.execute("SELECT id,claim,tenant FROM suite_jobs_v1 WHERE status='running'")
            )
        docker("kill", victim)
        hosts = [worker("host-a"), worker("host-b")]
        retried = set()
        deadline = time.monotonic() + 600
        started = time.monotonic()
        while True:
            jobs.expire()
            with database.connection() as db:
                failed = list(
                    db.execute("SELECT id,tenant,error FROM suite_jobs_v1 WHERE status='failed'")
                )
            for row in failed:
                assert row["error"] == "worker_lost", "unexpected execution/storage failure"
                if row["id"] not in retried:
                    old = next(x for x in stale if x["id"] == row["id"])
                    assert not jobs.finish(old["id"], old["claim"], "0" * 64, 0)
                    jobs.retry(row["tenant"], row["id"])
                    retried.add(row["id"])
            states = jobs.metrics(artifacts)["metrics"]
            if states["simweave_suite_jobs_succeeded"] == args.jobs:
                break
            if time.monotonic() > deadline:
                raise RuntimeError("distributed execution deadline exceeded")
            for host in hosts:
                if docker("inspect", "--format", "{{.State.Status}}", host) == "exited":
                    raise RuntimeError("worker host exited before completion")
            time.sleep(0.25)
        seconds = time.monotonic() - started
        assert len(retried) == 4
        for host in hosts:
            assert docker("wait", host) == "0"
            docker("cp", host + ":/tmp/verification.json", str(root / (host + ".json")))
        jobs.gate.set(True)
        maintenance.acknowledge_stopped(jobs, True)
        assert maintenance.drain(jobs, 0)["drained"]
        with database.connection() as db:
            rows = list(
                db.execute("SELECT id,tenant,artifact,attempt FROM suite_jobs_v1 ORDER BY id")
            )
        assert len(rows) == args.jobs and sum(r["attempt"] for r in rows) == args.jobs + 4
        for row in rows:
            assert jobs.get("beta" if row["tenant"] == "alpha" else "alpha", row["id"]) is None
            destination = root / "scratch/check.zip"
            artifacts.get(row["tenant"], row["artifact"], destination)
            destination.unlink()
        # Verify persistence across a real database restart, then the public API boundary.
        database.close()
        database = None
        docker("restart", pg)
        pg_port = docker("port", pg, "5432/tcp").rsplit(":", 1)[1]
        os.environ["SIMWEAVE_POSTGRES_DSN"] = (
            f"postgresql://postgres:synthetic-postgres-only@127.0.0.1:{pg_port}/simweave"
        )
        deadline = time.monotonic() + 60
        while True:
            try:
                database = Database(root / "scratch")
                break
            except RuntimeError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.5)
        jobs = Jobs(database)
        assert jobs.gate.paused()
        assert (
            jobs.metrics(SharedArtifacts(database, backend))["metrics"][
                "simweave_suite_jobs_succeeded"
            ]
            == args.jobs
        )
        jobs.gate.set(False)
        config_path = root / "api-storage.json"
        config_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "endpoint": f"https://127.0.0.1:{s3_port}",
                    "bucket": "simweave-fixture",
                    "ca_bundle": str(root / "ca.crt"),
                }
            )
        )
        os.environ["SIMWEAVE_S3_ACCESS_KEY"] = "synthetic-access"
        os.environ["SIMWEAVE_S3_SECRET_KEY"] = "synthetic-secret-only"
        settings = Settings(
            root / "api/runs.sqlite3",
            {
                "a" * 32: "alpha",
                "b" * 32: "beta",
                "i" * 32: {"tenant": "alpha", "subject": "fixture", "role": "importer"},
                "r" * 32: {"tenant": "alpha", "subject": "reader", "role": "reader"},
            },
            artifact_backend=config_path,
            postgres=True,
        )
        selected = next(row for row in rows if row["tenant"] == "alpha")

        def auth(letter):
            return {"Authorization": "Bearer " + letter * 32}

        with TestClient(create_app(settings)) as client:
            route = f"/api/v1/suite-jobs/{selected['id']}/artifact"
            response = client.get(route, headers=auth("a"))
            assert response.status_code == 200 and response.content[:2] == b"PK"
            assert client.get(route, headers=auth("b")).status_code == 404
            route = "/api/v1/catalog/builds/cluster/from-job"
            assert (
                client.post(route, json={"job": selected["id"]}, headers=auth("i")).status_code
                == 201
            )
            route = "/api/v1/catalog/builds/cluster/artifact"
            assert client.get(route, headers=auth("r")).content == response.content
        timings = []
        for host in hosts:
            for entry in json.loads((root / (host + ".json")).read_text()):
                timings.extend(entry["claim_ms"])
        result = {
            "schema_version": 1,
            "jobs": args.jobs,
            "worker_processes": 8,
            "container_hosts": 2,
            "physical_hosts": 1,
            "retried_worker_losses": 4,
            "missing_artifacts": 0,
            "database_restart": "passed",
            "api_artifact_catalog_flow": "passed",
            "cross_tenant_reads": 0,
            "execution_seconds": round(seconds, 3),
            "claim_p50_ms": round(statistics.median(timings), 3),
            "claim_p95_ms": round(sorted(timings)[int(0.95 * (len(timings) - 1))], 3),
            "claims_measured": len(timings),
            "transport": "TLS verified S3; PostgreSQL on isolated container network",
        }
        (root / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result), flush=True)
    finally:
        if database:
            database.close()
        for name in reversed(names):
            docker("rm", "-f", "-v", name)
        docker("network", "rm", prefix)
        (root / "server.key").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
