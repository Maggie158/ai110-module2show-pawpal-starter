"""Quick tests for PawPal+ core behaviors."""

from pawpal_system import Task, Pet


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
