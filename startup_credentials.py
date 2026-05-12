import os, json, base64, sys

def _write_credentials():
    path = "/tmp/google_credentials.json"
    b64 = os.getenv("GOOGLE_CREDENTIALS_B64", "").strip()
    if b64:
        try:
            raw = base64.b64decode(b64).decode("utf-8")
            json.loads(raw)
            with open(path, "w") as f:
                f.write(raw)
            os.environ["GOOGLE_CREDENTIALS_PATH"] = path
            print(f"✅ Google credentials written to {path}")
        except Exception as e:
            print(f"❌ Bad credentials: {e}", file=sys.stderr)
            sys.exit(1)

_write_credentials()