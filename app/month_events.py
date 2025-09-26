from __future__ import annotations

from typing import Dict, Optional

import pandas as pd
from flask import Flask, Response, json, jsonify, request

app = Flask(__name__)

JOB_STORE: Dict[str, Dict[str, pd.DataFrame]] = {}

DATE_CANDIDATES = [
    "事件日期(西元)",
    "事件日期",
    "日期",
    "date",
    "Date",
    "交易日",
    "event_date",
    "EventDate",
]


def _pick_date_col(df: pd.DataFrame) -> Optional[str]:
    cols = list(df.columns)
    for c in DATE_CANDIDATES:
        if c in cols:
            return c
    for c in cols:
        lc = str(c).lower()
        if "date" in lc or "日期" in lc:
            return c
    try:
        first = cols[0]
        pd.to_datetime(df[first], errors="raise")
        return first
    except Exception:
        return None


def df_to_records_safe(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%d")
    out = out.replace({pd.NA: None})
    return out.to_dict(orient="records")


@app.get("/api/month_events/<job_id>")
def api_month_events(job_id: str) -> Response:
    store = JOB_STORE.get(job_id)
    if not store or "events_df" not in store:
        return jsonify({"ok": False, "message": "job_id 不存在或尚無事件表"}), 404

    events = store["events_df"].copy()
    if events.empty:
        payload = {"ok": True, "rows": [], "n": 0}
        return Response(json.dumps(payload, ensure_ascii=False), mimetype="application/json")

    date_col = _pick_date_col(events) or ("事件日期" if "事件日期" in events.columns else None)
    if date_col is None:
        return Response(
            json.dumps({"ok": False, "message": "事件表無法辨識日期欄"}, ensure_ascii=False),
            mimetype="application/json",
            status=500,
        )

    events["_dt"] = pd.to_datetime(events[date_col], errors="coerce")

    ym = request.args.get("ym")
    month = request.args.get("month")
    year = request.args.get("year")
    limit = int(request.args.get("limit", 600))

    mask = events["_dt"].notna()
    if ym:
        ym = str(ym).strip()
        mask &= events["_dt"].dt.strftime("%Y-%m") == ym
    elif month:
        m = int(str(month).strip())
        mask &= events["_dt"].dt.month == m
        if year:
            y = int(str(year).strip())
            mask &= events["_dt"].dt.year == y

    out = events.loc[mask].drop(columns=["_dt"], errors="ignore").copy()
    out.sort_values(by=[date_col], inplace=True, kind="stable")
    n_all = int(len(out))
    if limit and n_all > limit:
        out = out.head(limit)

    payload = {
        "ok": True,
        "mode": "ym" if ym else ("cal" if month else "all"),
        "ym": ym,
        "month": month,
        "year": year,
        "n": n_all,
        "limit": limit,
        "limit_hit": n_all > limit,
        "rows": df_to_records_safe(out),
    }
    return Response(json.dumps(payload, ensure_ascii=False), mimetype="application/json")


if __name__ == "__main__":
    app.run(debug=True)
