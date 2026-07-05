"""PawPal+ demo script (CLI-first verification).

Temporary testing ground: builds an Owner with a couple of pets and some tasks,
then prints today's schedule to the terminal. Run it with:

    python main.py

This proves the backend logic in pawpal_system.py works before we wire it to
the Streamlit UI.
"""

from pawpal_system import Owner, Task, Scheduler, minutes_to_clock


def build_sample_owner() -> Owner:
    """Create an owner with two pets and a handful of tasks at different times."""
    owner = Owner(name="Jordan", available_minutes=120, day_start=8 * 60)

    # Pet 1: Mochi the dog
    mochi = owner.add_pet("Mochi", species="dog", breed="Shiba Inu")
    mochi.add_task(Task("Morning walk", duration_minutes=30, priority="high"))
    mochi.add_task(Task("Breakfast", duration_minutes=10, priority="high"))
    mochi.add_task(Task("Enrichment puzzle", duration_minutes=20, priority="low"))

    # Pet 2: Biscuit the cat (runs in its own parallel lane)
    biscuit = owner.add_pet("Biscuit", species="cat", breed="Tabby")
    biscuit.add_task(
        Task("Heart meds", duration_minutes=5, priority="high",
             preferred_time=9 * 60)  # owner wants this near 09:00
    )
    biscuit.add_task(Task("Feed", duration_minutes=10, priority="medium"))

    return owner


def print_schedule(owner: Owner, plan: dict) -> None:
    """Print today's schedule in a readable, grouped-by-pet format."""
    print("=" * 48)
    print(f"  Today's Schedule for {owner.name}")
    print(f"  Time budget: {owner.available_minutes} min/pet, "
          f"day starts {minutes_to_clock(owner.day_start)}")
    print("=" * 48)

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

    print("\n" + "=" * 48)


def main() -> None:
    owner = build_sample_owner()
    plan = Scheduler().build_plan(owner)
    print_schedule(owner, plan)


if __name__ == "__main__":
    main()
