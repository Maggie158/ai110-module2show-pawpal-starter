"""Quick tests for PawPal+ core behaviors."""

from datetime import date

from pawpal_system import Task, Pet, Owner, Scheduler


def test_mark_complete_changes_status():
    # A new task starts incomplete; mark_complete() should flip it to done.
    task = Task("Morning walk", duration_minutes=30, priority="high")
    assert task.done is False
    task.mark_complete()
    assert task.done is True


def test_adding_task_increases_pet_task_count():
    # Adding a task to a pet should grow that pet's task list by one.
    pet = Pet("Mochi", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Breakfast", duration_minutes=10))
    assert len(pet.tasks) == 1


def test_completing_daily_task_spawns_next_day():
    # A daily task, when completed, auto-creates a fresh instance due tomorrow.
    pet = Pet("Mochi", species="dog")
    task = pet.add_task(
        Task("Walk", 20, "high", frequency="daily", due_date=date(2026, 7, 5))
    )
    new_task = pet.complete_task(task)

    assert task.done is True
    assert new_task is not None
    assert new_task.due_date == date(2026, 7, 6)   # today + 1 day
    assert new_task.done is False
    assert len(pet.tasks) == 2                      # original + next occurrence


def test_once_task_does_not_recur():
    # A one-off task should not spawn a next occurrence when completed.
    pet = Pet("Mochi", species="dog")
    task = pet.add_task(Task("Vet visit", 30, frequency="once"))
    new_task = pet.complete_task(task)

    assert task.done is True
    assert new_task is None
    assert len(pet.tasks) == 1


def test_task_update_changes_fields():
    # update() edits an existing task in place instead of rebuilding it.
    task = Task("Walk", 30, "low", preferred_time=8 * 60)
    task.update(priority="high", preferred_time=9 * 60)
    assert task.priority == "high"
    assert task.preferred_time == 9 * 60


def test_task_update_rejects_invalid_and_rolls_back():
    # An invalid edit (empty description) is refused and the old value is kept.
    import pytest

    task = Task("Walk", 30, "high")
    with pytest.raises(ValueError):
        task.update(description="   ")
    assert task.description == "Walk"      # unchanged after rollback


def test_pet_update_renames():
    # Pet.update() changes only the fields passed in.
    pet = Pet("Mochi", species="dog")
    pet.update(name="Mo", species="cat")
    assert pet.name == "Mo"
    assert pet.species == "cat"


def test_owner_remove_pet_deletes_pet_and_its_tasks():
    # Removing a pet drops it (and its tasks) from the owner.
    owner = Owner("Jordan")
    mochi = owner.add_pet("Mochi")
    mochi.add_task(Task("Walk", 30))
    owner.add_pet("Biscuit")
    assert len(owner.pets) == 2

    owner.remove_pet(mochi)
    assert len(owner.pets) == 1
    assert owner.all_tasks() == []          # Mochi's task went with it


def test_detect_conflicts_flags_same_time_tasks():
    # Two tasks (different pets) at the exact same preferred time should warn.
    owner = Owner("Jordan")
    mochi = owner.add_pet("Mochi")
    biscuit = owner.add_pet("Biscuit")
    mochi.add_task(Task("Vitamins", 5, "high", preferred_time=9 * 60))
    biscuit.add_task(Task("Heart meds", 5, "high", preferred_time=9 * 60))

    warnings = Scheduler().detect_conflicts(owner)
    assert len(warnings) == 1
    assert "09:00" in warnings[0]


def test_no_conflict_when_times_differ():
    # Tasks at different times should produce no warning (and not crash).
    owner = Owner("Jordan")
    pet = owner.add_pet("Mochi")
    pet.add_task(Task("Walk", 30, preferred_time=8 * 60))
    pet.add_task(Task("Feed", 10, preferred_time=9 * 60))

    assert Scheduler().detect_conflicts(owner) == []


def test_done_and_untimed_tasks_are_not_conflicts():
    # A completed task and a task with no preferred time must not trigger warnings.
    owner = Owner("Jordan")
    pet = owner.add_pet("Mochi")
    done = pet.add_task(Task("Meds", 5, "high", preferred_time=9 * 60))
    done.mark_complete()
    pet.add_task(Task("Meds again", 5, "high", preferred_time=9 * 60))  # no partner now
    pet.add_task(Task("Anytime play", 15))                              # no preferred time

    assert Scheduler().detect_conflicts(owner) == []


# ---------------------------------------------------------------------------
# Sorting correctness  (Scheduler.sort_by_time)
# ---------------------------------------------------------------------------

def test_sort_by_time_returns_chronological_order():
    # Tasks added out of order should come back earliest-first.
    tasks = [
        Task("Evening", 30, preferred_time=18 * 60),
        Task("Morning", 10, preferred_time=7 * 60),
        Task("Afternoon", 20, preferred_time=14 * 60),
    ]
    ordered = Scheduler().sort_by_time(tasks)
    assert [t.description for t in ordered] == ["Morning", "Afternoon", "Evening"]


def test_sort_by_time_sends_untimed_tasks_to_the_end():
    # A task with no preferred time is treated as "end of day" and sorts last.
    tasks = [
        Task("No time set", 10),                       # preferred_time is None
        Task("Early", 10, preferred_time=6 * 60),
    ]
    ordered = Scheduler().sort_by_time(tasks)
    assert [t.description for t in ordered] == ["Early", "No time set"]


# ---------------------------------------------------------------------------
# Scheduling / packing  (Scheduler.build_plan)
# ---------------------------------------------------------------------------

def test_build_plan_empty_owner_returns_empty_lists():
    # An owner with no pets should plan without crashing.
    plan = Scheduler().build_plan(Owner("Jordan"))
    assert plan == {"scheduled": [], "skipped": []}


def test_build_plan_pet_with_no_tasks_schedules_nothing():
    # A pet that exists but has no tasks contributes nothing (edge case).
    owner = Owner("Jordan")
    owner.add_pet("Mochi")
    plan = Scheduler().build_plan(owner)
    assert plan["scheduled"] == []
    assert plan["skipped"] == []


def test_tasks_in_a_pet_lane_never_overlap():
    # Two same-time tasks must be packed back-to-back, not on top of each other.
    owner = Owner("Jordan", day_start=8 * 60)
    pet = owner.add_pet("Mochi")
    pet.add_task(Task("A", 30, "high", preferred_time=9 * 60))
    pet.add_task(Task("B", 20, "high", preferred_time=9 * 60))  # exact same time

    items = sorted(Scheduler().build_plan(owner)["scheduled"], key=lambda s: s["start"])
    assert len(items) == 2
    first, second = items
    assert second["start"] >= first["start"] + first["duration"]  # no overlap


def test_high_priority_is_scheduled_before_low():
    # Priority ordering: high is placed earlier in the lane than low.
    owner = Owner("Jordan", day_start=8 * 60)
    pet = owner.add_pet("Mochi")
    pet.add_task(Task("Low thing", 30, "low"))
    pet.add_task(Task("High thing", 30, "high"))

    order = [s["description"] for s in Scheduler().build_plan(owner)["scheduled"]]
    assert order.index("High thing") < order.index("Low thing")


def test_task_longer_than_budget_is_skipped():
    # A task that can't fit the daily budget is skipped, not scheduled.
    owner = Owner("Jordan", available_minutes=20)
    pet = owner.add_pet("Mochi")
    pet.add_task(Task("Long walk", 30, "high"))  # 30 > 20 budget

    plan = Scheduler().build_plan(owner)
    assert plan["scheduled"] == []
    assert len(plan["skipped"]) == 1
    assert plan["skipped"][0]["description"] == "Long walk"


def test_all_done_tasks_schedule_nothing():
    # Completed tasks are excluded from planning.
    owner = Owner("Jordan")
    pet = owner.add_pet("Mochi")
    t = pet.add_task(Task("Walk", 30, "high"))
    t.mark_complete()
    assert Scheduler().build_plan(owner)["scheduled"] == []


# ---------------------------------------------------------------------------
# Recurrence  (weekly) and weekday filtering
# ---------------------------------------------------------------------------

def test_completing_weekly_task_spawns_next_week():
    # A weekly task advances its due date by 7 days.
    pet = Pet("Mochi")
    task = pet.add_task(
        Task("Bath", 30, frequency="weekly", due_date=date(2026, 7, 5))
    )
    new_task = pet.complete_task(task)
    assert new_task is not None
    assert new_task.due_date == date(2026, 7, 12)  # +7 days


def test_weekly_task_only_scheduled_on_its_weekday():
    # A weekly task set for weekday 2 (Wed) should not appear when planning Monday.
    owner = Owner("Jordan")
    pet = owner.add_pet("Mochi")
    pet.add_task(Task("Wed grooming", 30, "high", frequency="weekly", weekday=2))

    monday_plan = Scheduler().build_plan(owner, weekday=0)
    wednesday_plan = Scheduler().build_plan(owner, weekday=2)
    assert monday_plan["scheduled"] == []
    assert len(wednesday_plan["scheduled"]) == 1


# ---------------------------------------------------------------------------
# Validation  (Task.__post_init__)
# ---------------------------------------------------------------------------

def test_task_rejects_invalid_input():
    # Bad Task fields should raise ValueError instead of creating a broken task.
    import pytest

    with pytest.raises(ValueError):
        Task("", 30)                       # empty description
    with pytest.raises(ValueError):
        Task("Walk", 0)                    # non-positive duration
    with pytest.raises(ValueError):
        Task("Walk", 30, priority="urgent")   # not a valid priority
    with pytest.raises(ValueError):
        Task("Walk", 30, frequency="hourly")   # not a valid frequency
