import time
import streamlit
from api import ApiClient
from datetime import date, datetime
from config import ADMIN_ID, API_BASE_URL, PAGES, ROLE_LABELS

from styles import (
    inject_styles,
    render_object_card,
    render_subobject_card,
    STATUS_KEY_TO_RU,
    STATUS_TO_CLASS,
)

# ============================ БАЗА ============================
streamlit.set_page_config(
    page_title="Стройка — админ",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@streamlit.cache_resource
def get_client() -> ApiClient:
    # заглушка-админ, при появлении реальной авторизации сюда токены/куки
    return ApiClient()


client = get_client()

# ============================ САЙДБАР
streamlit.sidebar.title("🌆 Админ-панель")
opts = list(PAGES.keys())

DEFAULT_PAGE = "objects" if "objects" in PAGES else opts[0]

q = streamlit.query_params


def _qp_get(qp, key: str, default=None):
    """Безопасно получить значение query-param: поддержка и строки, и списка."""
    v = qp.get(key, default)
    if isinstance(v, list):
        return v[0] if v else default
    return v


# Инициализация выбранной страницы: из URL, иначе дефолт
if "page" not in streamlit.session_state:
    requested = _qp_get(q, "page", None)
    streamlit.session_state.page = requested if requested in opts else DEFAULT_PAGE

# Радио, привязанное к session_state
page_key = streamlit.sidebar.radio(
    "Меню",
    options=opts,
    format_func=lambda k: f"{PAGES[k]['icon']} {PAGES[k]['label']}",
    key="page",
)

# Синхронизируем URL, только если отличается (чтобы не затирать руками поставленное)
if _qp_get(streamlit.query_params, "page") != streamlit.session_state.page:
    streamlit.query_params["page"] = streamlit.session_state.page

streamlit.title(f"{PAGES[page_key]['icon']} {PAGES[page_key]['label']}")
streamlit.sidebar.markdown("---")

# ============================ КЭШ
# ВАЖНО: keyword-only аргументы (через *) исключают случайную передачу client позиционно


@streamlit.cache_data(ttl=30)
def fetch_users_list(*, limit: int = 1000, offset: int = 0):
    try:
        return client.get("/users", params={"limit": limit, "offset": offset})
    except Exception:
        return None


@streamlit.cache_data(ttl=30)
def fetch_objects(*, user_id: int, limit: int = 500, offset: int = 0):
    return client.get(
        "/objects", params={"user_id": user_id, "limit": limit, "offset": offset}
    )


@streamlit.cache_data(ttl=30)
def fetch_object(*, object_id: int):
    return client.get(f"/objects/{object_id}")


@streamlit.cache_data(ttl=30)
def fetch_subobjects(*, object_id: int, limit: int = 500, offset: int = 0):
    return client.get(
        "/subobjects", params={"object_id": object_id, "limit": limit, "offset": offset}
    )


@streamlit.cache_data(ttl=30)
def fetch_checks_by_subobject(*, subobject_id: int, limit: int = 100, offset: int = 0):
    return client.get(
        "/checks",
        params={"subobject_id": subobject_id, "limit": limit, "offset": offset},
    )


streamlit.sidebar.markdown("---")
if streamlit.sidebar.button("🔄 Обновить кэши"):
    for fn in (
        fetch_users_list,
        fetch_objects,
        fetch_object,
        fetch_subobjects,
        fetch_checks_by_subobject,
    ):
        try:
            fn.clear()
        except Exception:
            pass
    streamlit.sidebar.success("Кэш очищен")


# ============================ УТИЛИТЫ
def optionize(items, id_key="object_id", name_key="name"):
    opts = []
    for it in items or []:
        _id = it.get(id_key)
        nm = (it.get(name_key) or "").strip()
        label = f"{_id} — {nm}" if nm else str(_id)
        opts.append({"label": label, "id": _id, "name": nm})
    return opts


def _as_list(payload, *containers):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in containers or ("items", "data", "results"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
    return []


def _first(d: dict, keys: list[str], default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _parse_dt(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, datetime.min.time())
    s = str(v).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            iv = int(float(s))
            if iv > 10_000_000_000:
                iv = iv / 1000.0
            return datetime.fromtimestamp(iv)
        except Exception:
            return None


def _fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y %H:%M") if dt else "—"


def _to_str(v) -> str | None:
    if v is None:
        return None
    if hasattr(v, "value"):
        return str(getattr(v, "value"))
    if isinstance(v, dict):
        return str(v.get("value") or v.get("name") or v.get("id") or v)
    return str(v)


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "да", "on"}


# ====== НОРМАЛИЗАЦИЯ К ПРОВЕРОЧНЫМ СХЕМАМ ======
def parse_checks_schema(payload) -> list[dict]:
    items = _as_list(payload, "items", "checks", "data", "checks_list")
    out = []
    for c in items:
        check = {
            "check_id": _first(c, ["check_id", "id"]),
            "subobject_id": _first(c, ["subobject_id", "subobjectId"]),
            "info": _first(c, ["info", "description"]),
            "location": _first(c, ["location", "place", "address"]),
            "status_check": _to_str(_first(c, ["status_check", "status", "state"])),
            "incident_status": _first(
                c, ["incident_status", "has_incidents", "incidents_exist"]
            ),
            "datetime": _parse_dt(
                _first(c, ["datetime", "date", "created_at", "createdAt", "timestamp"])
            ),
        }
        if check["incident_status"] is not None:
            check["incident_status"] = _to_bool(check["incident_status"])
        out.append(check)
    return out


def normalize_checks(payload):
    checks = parse_checks_schema(payload)
    rows = []
    for ch in checks:
        rows.append(
            {
                "ID": ch["check_id"],
                "Статус": ch["status_check"] or "—",
                "Описание": ch["info"] or "",
                "Место": ch["location"] or "",
                "Создано": _fmt_dt(ch["datetime"]),
                "Инциденты": "Да" if ch["incident_status"] else "Нет",
            }
        )
    return rows


# ====== НОРМАЛИЗАЦИЯ К ИНЦИДЕНТОПОДОБНЫМ СХЕМАМ ======
def parse_incidents_schema(payload) -> list[dict]:
    items = _as_list(payload, "items", "incidents", "data", "incidents_list")
    out = []
    for i in items:
        inc = {
            "incident_id": _first(i, ["incident_id", "id"]),
            "check_id": _first(i, ["check_id"]),
            "date": _parse_dt(
                _first(i, ["date", "datetime", "created_at", "createdAt", "timestamp"])
            ),
            "photo": _first(i, ["photo", "image", "image_url", "photo_url"]),
            "incident_status": _first(i, ["incident_status", "status", "active"]),
            "incident_info": _first(i, ["incident_info", "description", "info"]),
            "prescription_type": _to_str(
                _first(i, ["prescription_type", "prescriptionType"])
            ),
        }
        if inc["incident_status"] is not None:
            inc["incident_status"] = _to_bool(inc["incident_status"])
        out.append(inc)
    return out


def normalize_incidents(payload):
    incs = parse_incidents_schema(payload)
    rows = []
    for i in incs:
        rows.append(
            {
                "ID": i["incident_id"],
                "Описание": i["incident_info"] or "",
                "Статус": ("Да" if i["incident_status"] else "Нет")
                if i["incident_status"] is not None
                else "—",
                "Тип предписания": i["prescription_type"] or "",
                "Фото": i["photo"] or "",
                "Создано": _fmt_dt(i["date"]),
            }
        )
    return rows


def show_collapsible_df(
    title: str,
    rows: list[dict],
    *,
    key: str,
    empty_text: str = "Нет данных.",
    height: int = 360,
    expanded: bool = False,
):
    count = len(rows)
    with streamlit.expander(f"{title} — {count}", expanded=expanded):
        if count:
            streamlit.dataframe(
                rows, use_container_width=True, hide_index=True, height=height
            )
        else:
            streamlit.info(empty_text)


# ============================ СТРАНИЦЫ

# --------------------------- Пользователи
if page_key == "users":
    streamlit.caption("Создание и просмотр пользователей")

    # Создать пользователя
    with streamlit.expander("➕ Создать пользователя", expanded=True):
        u_cols = streamlit.columns(4)
        with u_cols[0]:
            u_name = streamlit.text_input("Имя пользователя", key="u_name")
        with u_cols[1]:
            u_password = streamlit.text_input(
                "Пароль", type="password", key="u_password"
            )
        with u_cols[2]:
            u_role_label = streamlit.selectbox(
                "Роль", list(ROLE_LABELS.values()), index=0, key="u_role"
            )
            inv_role = {v: k for k, v in ROLE_LABELS.items()}
            u_role = inv_role[u_role_label]
        with u_cols[3]:
            streamlit.write("")
            if streamlit.button("Создать", use_container_width=True):
                if not u_name or not u_password:
                    streamlit.warning("Заполните имя и пароль.")
                else:
                    try:
                        payload = {
                            "name": u_name,
                            "password": u_password,
                            "role": u_role,
                        }
                        created = client.post("/auth/register", payload)
                        streamlit.success("Пользователь создан")
                        streamlit.json(created, expanded=False)
                        try:
                            fetch_users_list.clear()
                        except Exception:
                            pass
                    except Exception as e:
                        streamlit.error(f"Ошибка создания: {e}")

    streamlit.markdown("---")

    # Список пользователей
    streamlit.subheader("Список пользователей")
    f1, f2, f3 = streamlit.columns([1, 2, 1])
    with f1:
        role_filter = streamlit.selectbox(
            "Фильтр по роли", ["Все"] + list(ROLE_LABELS.values())
        )
    with f2:
        name_filter = streamlit.text_input("Поиск по имени")
    with f3:
        streamlit.caption("Обновить кэш")
        if streamlit.button("Обновить пользователй", use_container_width=True):
            try:
                fetch_users_list.clear()
            except Exception:
                pass
            streamlit.success("Готово")
            time.sleep(0.2)

    try:
        users = fetch_users_list(limit=1000) or []
        rows = [
            {
                "ID": u.get("user_id"),
                "Имя": u.get("name"),
                "Роль": ROLE_LABELS.get(u.get("role"), u.get("role")),
            }
            for u in users
        ]
        # фильтры
        if role_filter != "Все":
            rows = [r for r in rows if r["Роль"] == role_filter]
        if name_filter.strip():
            nf = name_filter.strip().lower()
            rows = [
                r for r in rows if nf in (r["Имя"] or "").lower() or nf in str(r["ID"])
            ]

        if rows:
            streamlit.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            streamlit.info("Пока нет пользователей под выбранные фильтры.")
    except Exception as e:
        streamlit.error(f"Ошибка загрузки пользователей: {e}")

# ---------------------------  Объекты
elif page_key == "objects":
    inject_styles()
    # восстановим выбор из URL
    q = streamlit.query_params
    if "object_id" not in streamlit.session_state:
        streamlit.session_state["object_id"] = int(q.get("object_id", [0])[0] or 0)
    if "subobject_id" not in streamlit.session_state:
        streamlit.session_state["subobject_id"] = int(
            q.get("subobject_id", [0])[0] or 0
        )

    obj_id_state = "object_id"
    subobj_id_state = "subobject_id"

    # фильтры/обновление
    fcols = streamlit.columns([2, 1])
    with fcols[0]:
        name_filter = streamlit.text_input(
            "Фильтр по названию объекта", placeholder="Начните вводить имя…"
        )
    with fcols[1]:
        streamlit.caption("Обновить кэш списков")
        if streamlit.button("Обновить", use_container_width=True):
            try:
                fetch_objects.clear()
                fetch_object.clear()
                fetch_subobjects.clear()
            except Exception:
                pass
            streamlit.success("Кэш очищен")
            time.sleep(0.2)

    # список объектов
    try:
        obj_list = fetch_objects(user_id=int(ADMIN_ID)) or []
    except Exception as e:
        streamlit.error(f"Ошибка загрузки объектов: {e}")
        obj_list = []

    options = optionize(obj_list, id_key="object_id", name_key="name")
    if name_filter.strip():
        nf = name_filter.strip().lower()
        options = [
            o for o in options if nf in (o["name"] or "").lower() or nf in str(o["id"])
        ]

    # выбор объекта
    if options:
        idx = 0
        if streamlit.session_state[obj_id_state]:
            for i, o in enumerate(options):
                if o["id"] == streamlit.session_state[obj_id_state]:
                    idx = i
                    break
        selected_label = streamlit.selectbox(
            "Выберите объект", [o["label"] for o in options], index=idx
        )
        selected_obj_id = next(o["id"] for o in options if o["label"] == selected_label)
        streamlit.session_state[obj_id_state] = int(selected_obj_id)
        streamlit.query_params["object_id"] = str(selected_obj_id)
    else:
        selected_obj_id = None
        streamlit.info("Нет объектов. Создайте объект ниже.")

    streamlit.markdown("---")

    # Создание объекта / подобъекта
    ct1, ct2 = streamlit.columns(2)
    with ct1:
        with streamlit.expander("➕ Создать объект", expanded=False):
            with streamlit.form("form_create_object", clear_on_submit=True):
                new_obj_name = streamlit.text_input("Название объекта")
                new_obj_address = streamlit.text_input("Адрес (обязательно)")

                c_lat, c_lon = streamlit.columns(2)
                with c_lat:
                    new_obj_lat_str = streamlit.text_input(
                        "Широта (обязательно)", placeholder="например, 55.755826"
                    )
                with c_lon:
                    new_obj_lon_str = streamlit.text_input(
                        "Долгота (обязательно)", placeholder="например, 37.6173"
                    )

                try:
                    all_users = fetch_users_list(limit=1000) or []
                except Exception:
                    all_users = []

                def _by_role(users, role_key: str):
                    return [
                        u for u in users if (u.get("role") or "").lower() == role_key
                    ]

                admins = _by_role(all_users, "admin")
                inspectors = _by_role(all_users, "inspector")
                contractors = _by_role(all_users, "contractor")

                def _fmt_user(u):
                    return (
                        "— не назначать —"
                        if u is None
                        else f"{u.get('name') or 'user'} (id {u.get('user_id')})"
                    )

                # выпадашки с поиском по именам
                r1, r2, r3 = streamlit.columns(3)
                with r1:
                    admin_choice = streamlit.selectbox(
                        "Администратор", [None] + admins, format_func=_fmt_user
                    )
                with r2:
                    inspector_choice = streamlit.selectbox(
                        "Инспектор", [None] + inspectors, format_func=_fmt_user
                    )
                with r3:
                    contractor_choice = streamlit.selectbox(
                        "Подрядчик", [None] + contractors, format_func=_fmt_user
                    )

                submitted = streamlit.form_submit_button("Создать объект")

                if submitted:
                    # валидация и парс координат
                    def _parse_float(s: str) -> float | None:
                        s = (s or "").strip().replace(",", ".")
                        try:
                            return float(s)
                        except Exception:
                            return None

                    name = new_obj_name.strip()
                    addr = new_obj_address.strip()
                    lat = _parse_float(new_obj_lat_str)
                    lon = _parse_float(new_obj_lon_str)

                    if not name:
                        streamlit.warning("Укажите название объекта.")
                    elif lat is None or lon is None:
                        streamlit.warning("Укажите корректные координаты (числа).")
                    elif not (-90.0 <= lat <= 90.0):
                        streamlit.warning("Широта должна быть в диапазоне [-90; 90].")
                    elif not (-180.0 <= lon <= 180.0):
                        streamlit.warning(
                            "Долгота должна быть в диапазоне [-180; 180]."
                        )
                    else:
                        try:
                            payload = {
                                "name": name,
                                "object_lat": lat,
                                "object_lon": lon,
                            }
                            if addr:
                                payload["address"] = addr
                            if admin_choice:
                                payload["admin_id"] = int(admin_choice["user_id"])
                            if inspector_choice:
                                payload["inspector_id"] = int(
                                    inspector_choice["user_id"]
                                )
                            if contractor_choice:
                                payload["contractor_id"] = int(
                                    contractor_choice["user_id"]
                                )

                            created = client.post("/objects", payload)
                            streamlit.success("Объект создан")
                            streamlit.json(created, expanded=False)
                            try:
                                fetch_objects.clear()
                            except Exception:
                                pass
                        except Exception as e:
                            streamlit.error(f"Ошибка создания объекта: {e}")

    with ct2:
        with streamlit.expander("➕ Создать подобъект", expanded=False):
            with streamlit.form("form_create_subobject", clear_on_submit=True):
                so_new_name2 = streamlit.text_input(
                    "Название подобъекта", key="so_name_global"
                )
                so_new_presc2 = streamlit.text_area(
                    "Prescription info (опц.)", key="so_presc_global"
                )

                d1, d2 = streamlit.columns(2)
                with d1:
                    so_start_date = streamlit.date_input(
                        "Дата начала (опц.)", value=None, format="YYYY-MM-DD"
                    )
                with d2:
                    so_finish_date = streamlit.date_input(
                        "Дата окончания (опц.)", value=None, format="YYYY-MM-DD"
                    )

                if options:
                    lbl = streamlit.selectbox(
                        "Родительский объект",
                        [o["label"] for o in options],
                        index=idx if options else 0,
                    )
                    so_parent_id2 = next(o["id"] for o in options if o["label"] == lbl)
                else:
                    so_parent_id2 = streamlit.number_input(
                        "Object ID", min_value=1, step=1
                    )

                submitted2 = streamlit.form_submit_button("Создать подобъект")
                if submitted2:
                    if not so_new_name2.strip():
                        streamlit.warning("Укажите название подобъекта.")
                    else:
                        payload = {
                            "name": so_new_name2.strip(),
                            "object_id": int(so_parent_id2),
                        }
                        if so_new_presc2.strip():
                            payload["prescription_info"] = so_new_presc2.strip()

                        if so_start_date:
                            payload["start_date"] = so_start_date.isoformat()
                        if so_finish_date:
                            payload["finish_date"] = so_finish_date.isoformat()

                        try:
                            created = client.post("/subobjects", payload)
                            streamlit.success("Подобъект создан")
                            streamlit.json(created, expanded=False)
                            try:
                                fetch_subobjects.clear()
                            except Exception:
                                pass
                        except Exception as e:
                            streamlit.error(f"Ошибка создания подобъекта: {e}")

    c1, c2 = streamlit.columns([2, 3])
    streamlit.markdown("---")

    # ----- ОБЪЕКТ -----
    streamlit.markdown("### Объект")

    obj = None
    users = []
    users_index = {}

    if selected_obj_id:
        try:
            obj = fetch_object(object_id=int(selected_obj_id))
        except Exception as e:
            streamlit.error(f"Ошибка получения объекта: {e}")
    else:
        streamlit.caption("Выберите объект слева.")

    try:
        users = fetch_users_list(limit=1000) or []
        users_index = {
            u.get("user_id"): (u.get("name") or f"user {u.get('user_id')}")
            for u in users
        }
    except Exception:
        users, users_index = [], {}

    oc1, oc2 = streamlit.columns([2, 3])

    with oc1:
        streamlit.markdown("#### Детали")
        if obj:
            render_object_card(obj, users_index=users_index)

    with oc2:
        streamlit.markdown("#### Назначение ролей")

        def _by_role(users, role_key: str):
            return [u for u in users if (u.get("role") or "").lower() == role_key]

        admins = _by_role(users, "admin")
        inspectors = _by_role(users, "inspector")
        contractors = _by_role(users, "contractor")

        def _fmt_user(u: dict) -> str:
            return f"{u.get('name') or 'user'} (id {u.get('user_id')})"

        def _default_index(options: list[dict], current_id: int | None) -> int:
            if not options:
                return 0
            if current_id is None:
                return 0
            for i, u in enumerate(options):
                if u.get("user_id") == current_id:
                    return i
            return 0

        if obj:
            admin_idx = _default_index(admins, obj.get("admin_id"))
            insp_idx = _default_index(inspectors, obj.get("inspector_id"))
            contr_idx = _default_index(contractors, obj.get("contractor_id"))

            with streamlit.form("form_assign_roles", clear_on_submit=False):
                r1, r2, r3 = streamlit.columns(3)
                with r1:
                    if admins:
                        admin_choice = streamlit.selectbox(
                            "Администратор",
                            admins,
                            index=admin_idx,
                            format_func=_fmt_user,
                            key=f"admin_{selected_obj_id}",
                        )
                    else:
                        admin_choice = None
                        streamlit.warning("Нет пользователей с ролью admin")
                with r2:
                    if inspectors:
                        inspector_choice = streamlit.selectbox(
                            "Инспектор",
                            inspectors,
                            index=insp_idx,
                            format_func=_fmt_user,
                            key=f"insp_{selected_obj_id}",
                        )
                    else:
                        inspector_choice = None
                        streamlit.warning("Нет пользователей с ролью inspector")
                with r3:
                    if contractors:
                        contractor_choice = streamlit.selectbox(
                            "Подрядчик",
                            contractors,
                            index=contr_idx,
                            format_func=_fmt_user,
                            key=f"contr_{selected_obj_id}",
                        )
                    else:
                        contractor_choice = None
                        streamlit.warning("Нет пользователей с ролью contractor")

                save_roles = streamlit.form_submit_button("💾 Сохранить назначения")
                if save_roles:
                    if not (admin_choice and inspector_choice and contractor_choice):
                        streamlit.error("Нужно назначить все три роли.")
                    else:
                        try:
                            payload = {
                                "admin_id": int(admin_choice["user_id"]),
                                "inspector_id": int(inspector_choice["user_id"]),
                                "contractor_id": int(contractor_choice["user_id"]),
                            }
                            _ = client.put(f"/objects/{int(selected_obj_id)}", payload)
                            streamlit.success("Назначения обновлены")
                            try:
                                fetch_object.clear()
                                fetch_objects.clear()
                            except Exception:
                                pass
                            try:
                                obj = fetch_object(object_id=int(selected_obj_id))
                                render_object_card(obj, users_index=users_index)
                            except Exception:
                                pass
                        except Exception as e:
                            streamlit.error(f"Не удалось сохранить назначения: {e}")

        # ===== Подобъекты (ниже формы назначения) =====
        streamlit.markdown("#### Подобъекты объекта")
        sub_opts = []
        if selected_obj_id:
            try:
                resp = fetch_subobjects(object_id=int(selected_obj_id))
                subos = resp.get("subobjects") or []
                rows = [
                    {
                        "ID": so.get("subobject_id"),
                        "Название": so.get("name"),
                        "Статус инспектора": so.get("status_inspector"),
                        "Статус подрядчика": so.get("status_contractor"),
                        "Статус админа": so.get("status_admin"),
                    }
                    for so in subos
                ]

                show_collapsible_df(
                    "Подобъекты",
                    rows,
                    key=f"subobjects_{selected_obj_id}",
                    empty_text="У объекта пока нет подобъектов.",
                    height=360,
                    expanded=False,
                )

                sub_opts = optionize(subos, id_key="subobject_id", name_key="name")
            except Exception as e:
                streamlit.error(f"Ошибка получения подобъектов: {e}")
        else:
            streamlit.info("Нет объектов для отображения.")

    streamlit.markdown("---")

    if sub_opts:
        sidx = 0
        if streamlit.session_state.get(subobj_id_state):
            for i, o in enumerate(sub_opts):
                if o["id"] == streamlit.session_state[subobj_id_state]:
                    sidx = i
                    break

        chosen_label = streamlit.selectbox(
            "Выберите подобъект",
            [o["label"] for o in sub_opts],
            index=sidx,
            key="subobject_select_main",
        )
        chosen_so_id = next(o["id"] for o in sub_opts if o["label"] == chosen_label)
        streamlit.session_state[subobj_id_state] = int(chosen_so_id)
        streamlit.query_params["subobject_id"] = str(chosen_so_id)
    else:
        chosen_so_id = None
        streamlit.info("Нет подобъектов у этого объекта.")

    streamlit.markdown("### Подобъект")
    if chosen_so_id:
        dcols = streamlit.columns([2, 3])
        with dcols[0]:
            streamlit.markdown("#### Детали")
            try:
                so = client.get(f"/subobjects/{int(chosen_so_id)}")
                render_subobject_card(so)
            except Exception as e:
                streamlit.error(f"Ошибка загрузки подобъекта: {e}")
                so = None

        with dcols[1]:
            # ==== Редактирование статусов (админ)
            streamlit.markdown("#### Статусы участников")

            RU_TO_STATUS_KEY = {v: k for k, v in STATUS_KEY_TO_RU.items()}
            STATUS_CHOICES_RU = list(STATUS_TO_CLASS.keys())

            def _to_ru_and_token(raw: str | None) -> tuple[str, str]:
                if not raw:
                    return ("Не начато", "Не начато")
                raw = str(raw).strip()
                if raw in STATUS_CHOICES_RU:
                    return (raw, raw)
                if raw in STATUS_KEY_TO_RU:
                    return (STATUS_KEY_TO_RU[raw], raw)
                return ("Не начато", raw)

            def _to_outgoing(ru_value: str, original_token: str) -> str:
                if original_token in STATUS_KEY_TO_RU:
                    return RU_TO_STATUS_KEY.get(ru_value, RU_TO_STATUS_KEY["Не начато"])
                return ru_value

            cur_ins_ru, cur_ins_tok = _to_ru_and_token(
                so.get("status_inspector") if so else None
            )
            cur_con_ru, cur_con_tok = _to_ru_and_token(
                so.get("status_contractor") if so else None
            )
            cur_adm_ru, cur_adm_tok = _to_ru_and_token(
                so.get("status_admin") if so else None
            )

            with streamlit.form("form_edit_statuses", clear_on_submit=False):
                c1, c2 = streamlit.columns(2)
                with c1:
                    new_ins_ru = streamlit.selectbox(
                        "Статус инспектора",
                        STATUS_CHOICES_RU,
                        index=STATUS_CHOICES_RU.index(cur_ins_ru),
                        key=f"st_ins_{chosen_so_id}",
                    )
                    new_con_ru = streamlit.selectbox(
                        "Статус подрядчика",
                        STATUS_CHOICES_RU,
                        index=STATUS_CHOICES_RU.index(cur_con_ru),
                        key=f"st_con_{chosen_so_id}",
                    )
                with c2:
                    new_adm_ru = streamlit.selectbox(
                        "Статус админа",
                        STATUS_CHOICES_RU,
                        index=STATUS_CHOICES_RU.index(cur_adm_ru),
                        key=f"st_adm_{chosen_so_id}",
                    )

                saved = streamlit.form_submit_button("💾 Сохранить статусы")
                if saved:
                    try:
                        payload = {
                            "status_inspector": _to_outgoing(new_ins_ru, cur_ins_tok),
                            "status_contractor": _to_outgoing(new_con_ru, cur_con_tok),
                            "status_admin": _to_outgoing(new_adm_ru, cur_adm_tok),
                        }
                        updated = client.put(
                            f"/subobjects/{int(chosen_so_id)}", payload
                        )
                        streamlit.success("Статусы обновлены")

                        try:
                            fetch_subobjects.clear()
                        except Exception:
                            pass
                        try:
                            so = client.get(f"/subobjects/{int(chosen_so_id)}")
                            render_subobject_card(so)
                        except Exception:
                            pass
                    except Exception as e:
                        streamlit.error(f"Не удалось сохранить: {e}")

            streamlit.markdown("#### Проверки этого подобъекта")
            try:
                checks_payload = fetch_checks_by_subobject(
                    subobject_id=int(chosen_so_id), limit=50, offset=0
                )
                check_rows = normalize_checks(checks_payload)
                show_collapsible_df(
                    "Проверки этого подобъекта",
                    check_rows,
                    key=f"checks_{chosen_so_id}",
                    empty_text="Проверок пока нет.",
                    height=360,
                    expanded=False,
                )
            except Exception as e:
                streamlit.error(f"Ошибка загрузки проверок: {e}")
    else:
        streamlit.caption("Выберите подобъект, чтобы увидеть детали.")

    streamlit.markdown("---")

# --------------------------- Проверки, инциденты
elif page_key == "checks":
    # 1) Выбор объекта
    try:
        obj_list = fetch_objects(user_id=int(ADMIN_ID)) or []
        obj_opts = optionize(obj_list)
    except Exception:
        obj_opts = []

    if not obj_opts:
        streamlit.info("Нет объектов для отображения.")
    else:
        obj_label = streamlit.selectbox("Объект", [o["label"] for o in obj_opts])
        obj_id = next(o["id"] for o in obj_opts if o["label"] == obj_label)

        # 2) Выбор подобъекта
        try:
            subresp = fetch_subobjects(object_id=int(obj_id))
            subos = subresp.get("subobjects") or []
            sub_opts = optionize(subos, id_key="subobject_id", name_key="name")
        except Exception:
            sub_opts = []

        if not sub_opts:
            streamlit.info("Нет подобъектов для выбранного объекта.")
        else:
            sub_label = streamlit.selectbox("Подобъект", [s["label"] for s in sub_opts])
            so_id = next(s["id"] for s in sub_opts if s["label"] == sub_label)

            # 3) Список проверок по подобъекту
            try:
                checks_payload = fetch_checks_by_subobject(
                    subobject_id=int(so_id), limit=200, offset=0
                )
                check_rows = normalize_checks(checks_payload)
                if check_rows:
                    streamlit.subheader("Проверки")
                    streamlit.dataframe(
                        check_rows, use_container_width=True, hide_index=True
                    )
                else:
                    streamlit.info("Проверок пока нет.")
            except Exception as e:
                streamlit.error(f"Ошибка загрузки проверок: {e}")

            # 4) Инциденты по выбранной проверке
            streamlit.markdown("---")
            streamlit.subheader("Инциденты")
            if check_rows:
                view_label = streamlit.selectbox(
                    "Выберите проверку",
                    [
                        f"{r['ID']} — {r['Описание'] or 'без описания'}"
                        for r in check_rows
                    ],
                )
                chosen_check_id = int(str(view_label).split(" — ")[0])
                try:
                    incidents_payload = client.get(
                        "/incidents", params={"check_id": chosen_check_id}
                    )
                    inc_rows = normalize_incidents(incidents_payload)
                    if inc_rows:
                        streamlit.dataframe(
                            inc_rows, use_container_width=True, hide_index=True
                        )
                    else:
                        streamlit.info("Инцидентов нет.")
                except Exception as e:
                    streamlit.info(
                        "Ручка `/incidents` может быть не реализована или требует другой формат."
                    )
                    streamlit.caption(f"Техническая ошибка: {e}")

# --------------------------- Отчеты
elif page_key == "reports":
    streamlit.caption("Формирование отчетов")

    # выбор объекта
    try:
        obj_list = fetch_objects(user_id=int(ADMIN_ID)) or []
        obj_opts = optionize(obj_list, id_key="object_id", name_key="name")
    except Exception:
        obj_opts = []

    if not obj_opts:
        streamlit.info("Нет объектов для отображения.")
    else:
        col1, col2 = streamlit.columns([3, 1])
        with col1:
            obj_label = streamlit.selectbox("Объект", [o["label"] for o in obj_opts])
            selected_obj_id = next(o["id"] for o in obj_opts if o["label"] == obj_label)
        with col2:
            build = streamlit.button("Сформировать отчёт", use_container_width=True)

        if build:
            try:
                resp = fetch_subobjects(object_id=int(selected_obj_id))
                parent_obj = resp.get("object") or {}
                subos = resp.get("subobjects") or []
                object_name = parent_obj.get("name") or f"Объект {selected_obj_id}"

                def _parse_date(v):
                    if not v:
                        return None
                    if isinstance(v, date) and not isinstance(v, datetime):
                        return v
                    if isinstance(v, datetime):
                        return v.date()
                    s = str(v).strip()
                    if not s:
                        return None

                    try:
                        if "T" in s:
                            return datetime.fromisoformat(
                                s.replace("Z", "+00:00")
                            ).date()
                        return date.fromisoformat(s)
                    except Exception:
                        return None

                def _fmt_date(d: date | None) -> str:
                    return d.strftime("%d.%m.%Y") if d else "—"

                report_rows = []
                for so in subos:
                    start = _parse_date(so.get("start_date"))
                    finish = _parse_date(so.get("finish_date"))
                    duration = (finish - start).days if (start and finish) else None

                    report_rows.append(
                        {
                            "Подобъект": so.get("name")
                            or f"SO {so.get('subobject_id')}",
                            "Дата начала": _fmt_date(start),
                            "Дата конца": _fmt_date(finish),
                            "Длительность, дней": duration
                            if duration is not None
                            else "—",
                            "Доп. инфо": (so.get("prescription_info") or "").strip(),
                        }
                    )

                streamlit.subheader(f"Отчёт по объекту: {object_name}")
                if report_rows:
                    streamlit.dataframe(
                        report_rows, use_container_width=True, hide_index=True
                    )
                else:
                    streamlit.info("У объекта пока нет подобъектов.")

            except Exception as e:
                streamlit.error(f"Не удалось сформировать отчёт: {e}")

# --------------------------- Служебное
elif page_key == "tools":
    streamlit.subheader("Ping API")
    if streamlit.button("GET /"):
        try:
            streamlit.json(client.get("/"), expanded=False)
        except Exception as e:
            streamlit.error(f"Ошибка: {e}")
    streamlit.caption(f"API_BASE_URL = {API_BASE_URL}")
