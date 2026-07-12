"""Optional HTTP surface (FastAPI): POST /normalize.

Run:  uvicorn tamil_textprep.api:app --port 8032
Body: {"text": "...", "convention": "million", "engine": null}
Resp: {"text": "...", "report": [["H12_age:age","65","அறுபத்தைந்து"], ...]}

MCP exposure: this endpoint is the surface a future voxtn-mcp tool wraps
(one tool, `tamil_textprep_normalize`) — kept out of scope for this PR;
the JSON contract here is the stable interface.
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from . import __version__, normalize

app = FastAPI(title="tamil-textprep", version=__version__)


class NormalizeIn(BaseModel):
    text: str
    convention: str = "million"
    engine: str | None = None


@app.post("/normalize")
def normalize_ep(body: NormalizeIn):
    rows: list = []
    out = normalize(body.text, convention=body.convention,
                    engine=body.engine, report=rows)
    return {"text": out, "report": rows, "version": __version__}


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": __version__}
