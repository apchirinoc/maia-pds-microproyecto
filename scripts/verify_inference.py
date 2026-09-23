"""Comprueba una instalación de pruebas por HTTP. Crea dos registros de historial."""
import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import urllib.request
import uuid


def request(base, path, *, body=None, headers=None):
    req = urllib.request.Request(base.rstrip("/") + path, data=body, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--country", default="CO")
    args = parser.parse_args()
    password = os.environ.get("BNS_TEST_PASSWORD")
    if not password:
        parser.error("Defina BNS_TEST_PASSWORD con la contraseña de una cuenta del entorno de pruebas")
    ready = json.loads(request(args.api, "/ready"))
    assert ready["status"] == "ok" and not ready["simulatedInference"], ready
    login = json.loads(request(args.api, "/api/v1/auth/login", body=json.dumps({
        "username": args.username, "password": password,
    }).encode(), headers={"Content-Type": "application/json"}))
    auth = {"Authorization": "Bearer " + login["accessToken"]}
    image = args.image.read_bytes()
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(args.image.name)[0] or "application/octet-stream"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="countryCode"\r\n\r\n{args.country}\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="verification-image"\r\n'
        f'Content-Type: {mime}\r\n\r\n'
    ).encode() + image + f"\r\n--{boundary}--\r\n".encode()
    results = []
    for _ in range(2):
        result = json.loads(request(args.api, "/api/v1/classifications", body=body,
                                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}))
        assert result["simulatedInference"] is False
        assert result["persisted"] and result["uploadId"]
        assert result["imageSha256"] == hashlib.sha256(image).hexdigest()
        assert set(result["confidenceByClass"]) == {"glioma", "healthy", "meningioma", "pituitary"}
        assert abs(sum(result["confidenceByClass"].values()) - 100) < 0.03
        results.append(result)
    assert results[0]["uploadId"] != results[1]["uploadId"]
    assert results[0]["confidenceByClass"] == results[1]["confidenceByClass"]
    for _ in range(3):
        json.loads(request(args.api, "/api/v1/uploads/summary", headers=auth))
        csv = request(args.api, "/api/v1/uploads/export", headers=auth).decode()
        assert all(result["uploadId"] in csv for result in results), "CSV incompleto"
    print(json.dumps({"verified": True, "model": results[-1]["modelVersion"],
                      "uploads": [r["uploadId"] for r in results],
                      "imageSha256": results[-1]["imageSha256"]}, indent=2))


if __name__ == "__main__":
    main()
