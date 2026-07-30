"""HTML report builder for KxSweep / Ledger exports."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any


def findings_report(title: str, result: dict[str, Any]) -> str:
    findings = result.get("findings") or []
    rows = []
    for f in findings:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(f.get('severity', '')))}</td>"
            f"<td>{html.escape(str(f.get('title', '')))}</td>"
            f"<td>{html.escape(str(f.get('detail', '')))}</td>"
            "</tr>"
        )
    body_rows = "\n".join(rows) or "<tr><td colspan=3>No findings</td></tr>"
    now = datetime.now(timezone.utc).isoformat()
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{background:#05070a;color:#d7f7ff;font-family:ui-monospace,monospace;padding:24px}}
h1{{color:#00d9ff}} table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #134;padding:8px;text-align:left}} th{{color:#ff6600}}
.meta{{opacity:.8;margin-bottom:16px}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="meta">run_id={html.escape(str(result.get('run_id','')))} · status={html.escape(str(result.get('status','')))} · {html.escape(now)}</div>
<table><thead><tr><th>Severity</th><th>Title</th><th>Detail</th></tr></thead>
<tbody>
{body_rows}
</tbody></table>
</body></html>
"""
