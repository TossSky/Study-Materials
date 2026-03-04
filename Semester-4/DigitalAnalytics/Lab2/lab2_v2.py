import argparse
import requests
import matplotlib.pyplot as plt


BASE_URL = "https://ruz.spbstu.ru/api/v1/ruz"

WEEKDAYS = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье",
}


def search_teacher(query):
    url = f"{BASE_URL}/search/teachers"
    response = requests.get(url, params={"q": query})
    response.raise_for_status()
    data = response.json()
    teachers = data.get("teachers", [])
    if not teachers:
        print(f"[-] Преподаватель '{query}' не найден")
        return None
    teacher = teachers[0]
    print(f"[+] Найден преподаватель: {teacher['full_name']} (id={teacher['id']})")
    return teacher


def get_schedule(teacher_id):
    url = f"{BASE_URL}/teachers/{teacher_id}/scheduler"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def print_schedule(schedule):
    week = schedule.get("week", {})
    is_odd = week.get("is_odd", False)
    week_type = "нечётная" if is_odd else "чётная"
    print(f"\nНеделя: {week_type} ({week.get('date_start', '')} — {week.get('date_end', '')})")
    print("=" * 80)

    for day in schedule.get("days", []):
        weekday = WEEKDAYS.get(day["weekday"], str(day["weekday"]))
        date = day.get("date", "")
        lessons = day.get("lessons", [])
        if not lessons:
            continue
        print(f"\n{weekday} ({date}):")
        print("-" * 60)
        for lesson in lessons:
            subject = lesson.get("subject", "—")
            time_start = lesson.get("time_start", "")
            time_end = lesson.get("time_end", "")
            lesson_type = lesson.get("typeObj", {}).get("name", "")
            groups = ", ".join(
                g.get("name", "") for g in (lesson.get("groups") or [])
            )
            auditories = ", ".join(
                f"{a.get('name', '')} ({a.get('building', {}).get('abbr', '')})"
                for a in (lesson.get("auditories") or [])
            )
            parity = lesson.get("parity", 0)
            parity_str = ""
            if parity == 1:
                parity_str = " [нечёт.]"
            elif parity == 2:
                parity_str = " [чёт.]"

            print(f"  {time_start}–{time_end} | {subject} ({lesson_type}){parity_str}")
            print(f"    Группы: {groups or '—'}")
            print(f"    Аудитория: {auditories or '—'}")


def plot_schedule(schedule):
    day_counts = {}
    for day in schedule.get("days", []):
        weekday = day["weekday"]
        day_name = WEEKDAYS.get(weekday, str(weekday))
        day_counts[day_name] = len(day.get("lessons", []))

    ordered_days = []
    ordered_counts = []
    for wd in sorted(WEEKDAYS.keys()):
        name = WEEKDAYS[wd]
        if name in day_counts:
            ordered_days.append(name)
            ordered_counts.append(day_counts[name])

    plt.figure(figsize=(10, 6))
    plt.bar(ordered_days, ordered_counts, color="steelblue")
    plt.xlabel("День недели")
    plt.ylabel("Количество занятий")
    plt.title("Расписание преподавателя по дням недели")
    plt.tight_layout()
    plt.savefig("schedule_teacher.png", dpi=150)
    print("\n[+] График сохранён в schedule_teacher.png")
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Получение расписания по преподавателю с ruz.spbstu.ru"
    )
    parser.add_argument("teacher", type=str, help="ФИО преподавателя (например, Иванов)")
    args = parser.parse_args()

    teacher = search_teacher(args.teacher)
    if teacher is None:
        return

    schedule = get_schedule(teacher["id"])
    print_schedule(schedule)
    plot_schedule(schedule)


if __name__ == "__main__":
    main()
