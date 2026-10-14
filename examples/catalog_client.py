"""Minimal catalog client. Set SIMWEAVE_API_TOKEN in the caller's environment."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward credentials to a redirected origin.
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("show")
    upload = commands.add_parser("import")
    upload.add_argument("bundle", type=Path)
    upload.add_argument("--build", required=True)
    approve = commands.add_parser("promote")
    approve.add_argument("--build", required=True)
    approve.add_argument("--policy", required=True, type=Path)
    approve.add_argument("--generation", type=int, required=True)
    approve.add_argument("--reason", required=True)
    args = parser.parse_args()
    url = urlsplit(args.url)
    if (
        (
            url.scheme != "https"
            and not (url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1"))
        )
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        parser.error("use HTTPS, or HTTP on loopback, with no embedded credentials/query")
    headers = {"Authorization": "Bearer " + os.environ["SIMWEAVE_API_TOKEN"]}
    method, path, data = "GET", "/api/v1/catalog", None
    if args.action == "import":
        if args.bundle.stat().st_size > 128 * 1024 * 1024:
            parser.error("bundle exceeds 128 MiB")
        method, path = "PUT", path + "/builds/" + quote(args.build, safe="")
        data = args.bundle.read_bytes()
        headers["Content-Type"] = "application/zip"
    elif args.action == "promote":
        method, path = "POST", path + "/promote"
        if args.policy.stat().st_size > 65536:
            parser.error("policy exceeds 64 KiB")
        data = json.dumps(
            {
                "build": args.build,
                "expected_generation": args.generation,
                "reason": args.reason,
                "policy": json.loads(args.policy.read_text(encoding="utf-8")),
            }
        ).encode()
        headers["Content-Type"] = "application/json"
    with build_opener(NoRedirect).open(
        Request(args.url.rstrip("/") + path, data=data, headers=headers, method=method), timeout=120
    ) as response:
        print(response.read(4 * 1024 * 1024).decode())


if __name__ == "__main__":
    main()
