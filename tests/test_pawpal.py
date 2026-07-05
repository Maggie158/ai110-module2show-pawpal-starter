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
