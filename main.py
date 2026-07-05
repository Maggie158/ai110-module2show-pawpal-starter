"""PawPal+ demo script (CLI-first verification).

Temporary testing ground: builds an Owner with a couple of pets and some tasks,
then prints today's schedule and demos the sorting/filtering algorithms. Run:

    python main.py

This proves the backend logic in pawpal_system.py works before we wire it to
the Streamlit UI.
"""

from pawpal_system import Owner, Task, Scheduler, minutes_to_clock


def build_sample_owner() -> Owner:
    """Create an owner with two pets. Tasks are added OUT OF ORDER by time on
    purpose, so sort_by_time() has something to fix."""
    owner = Owner(name="Jordan", available_minutes=120, day_start=7 * 60)

    # Pet 1: Mochi the dog — note the times are 18:00, 07:00, 14:00 (not sorted)
    mochi = owner.add_pet("Mochi", species="dog", breed="Shiba Inu")
    mochi.add_task(Task("Evening walk", 30, "medium", preferred_time=18 * 60))
    mochi.add_task(Task("Breakfast", 10, "high", preferred_time=7 * 60))
    mochi.add_task(Task("Enrichment puzzle", 20, "low", preferred_time=14 * 60))

    # Pet 2: Biscuit the cat — runs in its own parallel lane
    biscuit = owner.add_pet("Biscuit", species="cat", breed="Tabby")
    biscuit.add_task(Task("Heart meds", 5, "high", preferred_time=9 * 60))
    biscuit.add_task(Task("Feed", 10, "medium", preferred_time=8 * 60))

    # Deliberate clash: Mochi's vitamins are set for 09:00, same as Biscuit's
    # heart meds — the owner can't do both at once, so this should warn.
    mochi.add_task(Task("Vitamins", 5, "high", preferred_time=9 * 60))

    return owner


def print_schedule(owner: Owner, plan: dict) -> None:
    """Print today's schedule in a readable, grouped-by-pet format."""
    print("=" * 52)
    print(f"  Today's Schedule for {owner.name}")
    print(f"  Time budget: {owner.available_minutes} min/pet, "
          f"day starts {minutes_to_clock(owner.day_start)}")
    print("=" * 52)

    for pet in owner.pets:
        items = [s for s in plan["scheduled"] if s["pet"] == pet.name]
        print(f"\n🐾 {pet.name} ({pet.species})")
        if not items:
            print("   (nothing scheduled)")
        for s in items:
            print(f"   {s['clock']}  {s['description']:<20} "
                  f"({s['duration']} min) [{s['priority']}]")
            print(f"          ↳ {s['reason']}")

    if plan["skipped"]:
        print("\n⚠️  Skipped (ran out of time):")
        for s in plan["skipped"]:
            print(f"   - {s['pet']}: {s['description']} — {s['reason']}")


def demo_sort_by_time(owner: Owner) -> None:
    """Show Scheduler.sort_by_time() putting Mochi's tasks into clock order."""
    scheduler = Scheduler()
    mochi = owner.pets[0]

    print("\n" + "-" * 52)
    print("  Sorting demo: Mochi's tasks (added out of order)")
    print("-" * 52)
    print("  As entered:")
    for t in mochi.tasks:
        print(f"     {minutes_to_clock(t.preferred_time)}  {t.description}")
    print("  Sorted by time:")
    for t in scheduler.sort_by_time(mochi.tasks):
        print(f"     {minutes_to_clock(t.preferred_time)}  {t.description}")


def demo_conflicts(owner: Owner) -> None:
    """Show Scheduler.detect_conflicts() warning about same-time tasks."""
    scheduler = Scheduler()
    print("\n" + "-" * 52)
    print("  Conflict detection demo")
    print("-" * 52)
    warnings = scheduler.detect_conflicts(owner)
    if warnings:
        for w in warnings:
            print(f"   ⚠️  {w}")
    else:
        print("   ✅ No conflicts found.")


def demo_recurring(owner: Owner) -> None:
    """Show that completing a recurring task auto-creates the next occurrence."""
    mochi = owner.pets[0]
    breakfast = mochi.tasks[1]  # daily "Breakfast"

    print("\n" + "-" * 52)
    print("  Recurring demo: completing a daily task")
    print("-" * 52)
    print(f"  Completing '{breakfast.description}' (frequency: {breakfast.frequency})...")
    new_task = mochi.complete_task(breakfast)
    print(f"     {breakfast.description} done: {breakfast.done}")
    if new_task is not None:
        print(f"     Auto-created next occurrence '{new_task.description}' "
              f"due {new_task.due_date} (today + 1 day)")


def demo_filtering(owner: Owner) -> None:
    """Show Owner.filter_tasks() by completion status and by pet name."""
    print("\n" + "-" * 52)
    print("  Filtering demo")
    print("-" * 52)

    print("  Pending tasks (not done):")
    for t in owner.filter_tasks(status="pending"):
        print(f"     [ ] {t.description}")

    print("  Completed tasks:")
    for t in owner.filter_tasks(status="done"):
        print(f"     [x] {t.description}")

    print("  Only Biscuit's tasks:")
    for t in owner.filter_tasks(pet_name="Biscuit"):
        print(f"     {t.description}")


def main() -> None:
    owner = build_sample_owner()
    plan = Scheduler().build_plan(owner)
    print_schedule(owner, plan)
    demo_sort_by_time(owner)
    demo_conflicts(owner)
    demo_recurring(owner)
    demo_filtering(owner)
    print("\n" + "=" * 52)


if __name__ == "__main__":
    main()
