import requests

BASE = "https://ruz.spbstu.ru/api/v1/ruz"


def _get(url, **params):
    return requests.get(url, params=params).json()


def _lessons(data, date):
    for d in data.get("days", []):
        if d.get("date") == date:
            return d.get("lessons", [])
    return []


def _fmt(lessons):
    if not lessons:
        return None
    r = ""
    for l in lessons:
        ts = ",".join(t.get("full_name", "") for t in (l.get("teachers") or []))
        gs = ",".join(g.get("name", "") for g in (l.get("groups") or []))
        ps = ",".join(a.get("name", "") for a in (l.get("auditories") or []))
        r += f"Time:{l.get('time_start', '')}-{l.get('time_end', '')}\n"
        r += f"Subject:{l.get('subject', '')}\n"
        r += f"Type:{(l.get('typeObj') or {}).get('name', '')}\n"
        r += f"Teacher:{ts or 'None'}\n"
        r += f"Groups:{gs or 'None'}\n"
        r += f"Place:{ps or 'None'}\n"
    return r


def get_group_schedule(group, date):
    groups = _get(f"{BASE}/search/groups", q=group).get("groups") or []
    if not groups:
        return None
    gid = next((g["id"] for g in groups if g.get("name") == group), groups[0]["id"])
    return _fmt(_lessons(_get(f"{BASE}/scheduler/{gid}", date=date), date))


def get_teacher_schedule(teacher, date):
    q = teacher.split()[0] if teacher.strip() else teacher
    teachers = _get(f"{BASE}/search/teachers", q=q).get("teachers") or []
    if not teachers:
        return None
    tid = next((t["id"] for t in teachers if t.get("full_name") == teacher), teachers[0]["id"])
    return _fmt(_lessons(_get(f"{BASE}/teachers/{tid}/scheduler", date=date), date))


def get_room_schedule(building, room, date):
    buildings = _get(f"{BASE}/buildings").get("buildings") or []
    bid = next((b["id"] for b in buildings if building in (b.get("name"), b.get("abbr"))), None)
    if bid is None:
        return None
    rooms = _get(f"{BASE}/buildings/{bid}/rooms").get("rooms") or []
    rid = next((r["id"] for r in rooms if r.get("name") == room), None)
    if rid is None:
        return None
    return _fmt(_lessons(_get(f"{BASE}/buildings/{bid}/rooms/{rid}/scheduler", date=date), date))
