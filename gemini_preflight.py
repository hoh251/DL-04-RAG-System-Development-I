"""Validate Gemini credentials and model availability without displaying the key."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import config

ROOT = Path(__file__).resolve().parent


def check_gemini():
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "provider": "gemini", "model": config.LLM_MODEL,
              "inference_tested": False, "key_value_saved": False}
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        return {**result, "status": "missing_key", "message": "Set GOOGLE_API_KEY or GEMINI_API_KEY, or run RUN-AI.cmd to enter it privately."}
    if config.LLM_PROVIDER != "gemini":
        return {**result, "status": "invalid_provider", "message": "Gemini launcher requires the gemini provider."}
    names = []
    page = None
    try:
        for _ in range(10):
            params = {"pageSize": 100}
            if page:
                params["pageToken"] = page
            request = Request("https://generativelanguage.googleapis.com/v1beta/models?" + urlencode(params),
                              headers={"x-goog-api-key": key})
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)
            names.extend(m["name"].removeprefix("models/") for m in payload.get("models", [])
                         if "generateContent" in m.get("supportedGenerationMethods", []))
            page = payload.get("nextPageToken")
            if not page:
                break
    except HTTPError as error:
        return {**result, "status": "http_error", "http_status": error.code,
                "message": "Gemini rejected model discovery; check key restrictions, account permissions and quota. No key was logged."}
    except (URLError, TimeoutError):
        return {**result, "status": "network_error", "message": "Cannot reach Gemini model discovery. Check internet or sandbox permissions."}
    if config.LLM_MODEL not in names:
        return {**result, "status": "model_unavailable", "available_text_models": sorted(names),
                "message": "Selected model was not returned for this key. Set RAG_GEMINI_MODEL to an available model explicitly."}
    return {**result, "status": "ready", "model_list_verified": True,
            "message": "Key accepted for model discovery; inference still requires a live test."}


def save_result(result):
    folder = ROOT / "evidence/gemini"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "preflight.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    result = check_gemini()
    save_result(result)
    print(result["status"] + ": " + result["message"])
    raise SystemExit(0 if result["status"] == "ready" else 2)
