import re
import streamlit

STATUS_TO_CLASS = {
    "Выполнено": "ok",
    "В работе": "progress",
    "Не начато": "todo",
    "Приостановлено": "paused",
}

# поддержка Enum, если прилетят
STATUS_KEY_TO_RU = {
    "COMPLETED": "Выполнено",
    "IN_PROGRESS": "В работе",
    "NOT_STARTED": "Не начато",
    "ON_HOLD": "Приостановлено",
}


def _first(d: dict, keys: list[str]):
    for k in keys:
        if d.get(k) is not None:
            return d.get(k)
    return None


def inject_styles():
    streamlit.markdown(
        """
        <style>
        .card{border:1px solid #E5E7EB;border-radius:12px;padding:16px;background:#fff;}
        .card h3{margin:0 0 .5rem 0;font-weight:600;}
        .muted{color:#6B7280;}
        .kv{display:grid;grid-template-columns:160px 1fr;gap:.35rem 1rem;}
        .pill{display:inline-block;padding:.15rem .55rem;border-radius:999px;background:#F3F4F6;
              font-size:.85rem;margin-right:.35rem;}
        .pill.ok{background:#ECFDF5;}
        .pill.progress{background:#EFF6FF;}
        .pill.paused{background:#FEF3C7;}
        .pill.todo{background:#F3F4F6;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_status(value):
    if not value:
        return "—", ""
    v = str(value).strip()

    if v in STATUS_TO_CLASS:
        return v, STATUS_TO_CLASS[v]

    key = re.sub(r"\W+", "_", v).upper()
    if key in STATUS_KEY_TO_RU:
        ru = STATUS_KEY_TO_RU[key]
        return ru, STATUS_TO_CLASS.get(ru, "")

    return v, ""


def render_object_card(
    payload: dict,
    *,
    users_index: dict[int, str] | None = None,
):
    users_index = users_index or {}

    o = (
        payload.get("object")
        if isinstance(payload, dict) and "object" in payload
        else payload or {}
    )
    if not isinstance(o, dict):
        streamlit.info("Нет данных по объекту.")
        return

    object_id = _first(o, ["object_id", "id"])
    name = o.get("name") or f"Объект {object_id}"
    address = _first(o, ["address", "addr", "location"]) or "—"

    lat = o.get("object_lat")
    lon = o.get("object_lon")
    coords = (
        f"{lat:.6f}, {lon:.6f}"
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float))
        else "—"
    )

    raw_status = _first(o, ["status", "status_object"])
    status_ru, status_cls = normalize_status(raw_status)

    def uname(uid):
        if uid is None:
            return "—"
        nm = users_index.get(uid)
        return f"{nm} (id {uid})" if nm else f"id {uid}"

    admin = uname(o.get("admin_id"))
    insp = uname(o.get("inspector_id"))
    contr = uname(o.get("contractor_id"))

    sid = object_id if object_id is not None else "—"
    s_badge = (
        f'<span class="pill {status_cls}">Статус: {status_ru}</span>'
        if status_ru != "—"
        else ""
    )

    streamlit.markdown(
        f"""
        <div class="card">
          <h3>🏗️ {name} <span class="muted">#{sid}</span></h3>
          <div style="margin:.25rem 0 .75rem 0;">{s_badge}</div>
          <div class="kv">
            <div class="muted">Адрес</div><div>{address}</div>
            <div class="muted">Координаты</div><div>{coords}</div>
            <div class="muted">Админ</div><div>{admin}</div>
            <div class="muted">Инспектор</div><div>{insp}</div>
            <div class="muted">Подрядчик</div><div>{contr}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_subobject_card(so: dict):
    sid = so.get("subobject_id")
    name = so.get("name") or f"Подобъект {sid}"

    s_i_raw = so.get("status_inspector")
    s_c_raw = so.get("status_contractor")
    s_a_raw = so.get("status_admin")

    s_i, ci = normalize_status(s_i_raw)
    s_c, cc = normalize_status(s_c_raw)
    s_a, ca = normalize_status(s_a_raw)

    start_date = so.get("start_date") or "—"
    finish_date = so.get("finish_date") or "—"

    streamlit.markdown(
        f"""
        <div class="card">
          <h3>🏢 {name} <span class="muted">#{sid}</span></h3>
          <div style="margin:.25rem 0 .75rem 0;">
            <span class="pill {ci}">Инспектор: {s_i}</span>
            <span class="pill {cc}">Подрядчик: {s_c}</span>
            <span class="pill {ca}">Админ: {s_a}</span>
          </div>
          <div class="kv">
            <div class="muted">Начало работ</div><div>{start_date}</div>
            <div class="muted">Окончание работ</div><div>{finish_date}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
