"""PawPal+ logic layer.

Backend classes for the pet-care planner. No Streamlit here — this module is
pure logic so it can be verified from a CLI/demo script and unit tests before
being wired to the UI ("CLI-first" workflow).

Four classes:
    Task      - a single care activity (description, time, frequency, done)
    Pet       - pet details + its list of tasks
    Owner     - manages multiple pets and exposes all their tasks
    Scheduler - the "brain": retrieves, organizes, and plans tasks across pets

Scheduling rule: each pet is its own lane. Tasks within a pet are placed back
to back (no overlap) in priority order; different pets run in parallel, so two
pets can share the same time slot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Higher number = more important, so "high" priority tasks get placed first.
PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}

VALID_PRIORITIES = set(PRIORITY_RANK)
VALID_FREQUENCIES = {"once", "daily", "weekly"}


def minutes_to_clock(minutes: int) -> str:
    """Convert minutes-from-midnight into a 'HH:MM' 24-hour string."""
    minutes = int(minutes)
    return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single care activity for a pet.

    Attributes:
        description: What to do, e.g. "Morning walk".
        duration_minutes: How long the activity takes (its "time").
        priority: "low" | "medium" | "high".
        frequency: "once" | "daily" | "weekly" (how often it recurs).
        weekday: For weekly tasks, 0=Mon..6=Sun. Ignored for other frequencies.
        preferred_time: Optional minutes-from-midnight the owner wants it near.
        done: Completion status. Done tasks are skipped when planning.
    """

    description: str
    duration_minutes: int = 30
    priority: str = "medium"
    frequency: str = "daily"
    weekday: Optional[int] = None
    preferred_time: Optional[int] = None
    done: bool = False

    def __post_init__(self) -> None:
        if not self.description or not self.description.strip():
            raise ValueError("Task description cannot be empty.")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive.")
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(VALID_PRIORITIES)}.")
        if self.frequency not in VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {sorted(VALID_FREQUENCIES)}.")

    def mark_complete(self) -> None:
        """Mark this task complete."""
        self.done = True

    def priority_rank(self) -> int:
        """Return a sortable number for the priority (high=3, low=1)."""
        return PRIORITY_RANK[self.priority]

    def occurs_on(self, weekday: Optional[int]) -> bool:
        """Whether this task should be planned for the given weekday (0=Mon).

        Pass weekday=None to ignore the day (treat every task as due). Done
        tasks never occur.
        """
        if self.done:
            return False
        if self.frequency in ("once", "daily"):
            return True
        # weekly: only on its chosen weekday (or any day if none set / not asked)
        if weekday is None or self.weekday is None:
            return True
        return self.weekday == weekday


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str = "dog"
    breed: str = ""
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> Task:
        """Attach a task to this pet and return it."""
        self.tasks.append(task)
        return task

    def remove_task(self, task: Task) -> None:
        """Detach a task from this pet (no error if it's already gone)."""
        if task in self.tasks:
            self.tasks.remove(task)

    def list_tasks(self) -> List[Task]:
        """Return this pet's tasks."""
        return list(self.tasks)


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """The app user: manages pets and exposes all their tasks.

    available_minutes is the daily time budget per pet lane; day_start is when
    the care day begins (minutes-from-midnight, default 08:00).
    """

    name: str
    available_minutes: int = 180
    day_start: int = 8 * 60
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, name: str, species: str = "dog", breed: str = "") -> Pet:
        """Register a new pet and return it."""
        if not name or not name.strip():
            raise ValueError("Pet name cannot be empty.")
        pet = Pet(name=name.strip(), species=species, breed=breed)
        self.pets.append(pet)
        return pet

    def list_pets(self) -> List[Pet]:
        """Return this owner's pets."""
        return list(self.pets)

    def all_tasks(self) -> List[Task]:
        """Provide access to every task across all pets (flattened)."""
        return [task for pet in self.pets for task in pet.tasks]


# ---------------------------------------------------------------------------
# Scheduler — the brain
# ---------------------------------------------------------------------------

class Scheduler:
    """Retrieves, organizes, and plans an owner's tasks across their pets.

    build_plan() is the one public entry point; the rest are helpers.
    """

    def build_plan(self, owner: Owner, weekday: Optional[int] = None) -> Dict:
        """Build a daily plan for every pet.

        Returns a dict:
            {
              "scheduled": [ {pet, start, clock, description, duration,
                              priority, reason}, ... ],   # ordered by pet then time
              "skipped":   [ {pet, description, reason}, ... ],
            }
        Each pet is planned independently (its own parallel lane).
        """
        scheduled: List[Dict] = []
        skipped: List[Dict] = []

        for pet in owner.pets:
            pet_scheduled, pet_skipped = self._plan_for_pet(pet, owner, weekday)
            scheduled.extend(pet_scheduled)
            skipped.extend(pet_skipped)

        return {"scheduled": scheduled, "skipped": skipped}

    # -- helpers ------------------------------------------------------------

    def _plan_for_pet(self, pet: Pet, owner: Owner, weekday: Optional[int]):
        """Lay one pet's due tasks into its lane, in priority order.

        Returns (scheduled_list, skipped_list) for this pet.
        """
        due = [t for t in pet.tasks if t.occurs_on(weekday)]
        ordered = self._sort_by_priority(due)

        scheduled: List[Dict] = []
        skipped: List[Dict] = []

        cursor = owner.day_start        # next free minute in this pet's lane
        used = 0                        # minutes of budget spent

        for task in ordered:
            # Filtering: respect the owner's daily time budget (per pet lane).
            if used + task.duration_minutes > owner.available_minutes:
                remaining = owner.available_minutes - used
                skipped.append({
                    "pet": pet.name,
                    "description": task.description,
                    "reason": (
                        f"Only {remaining} min left in {pet.name}'s "
                        f"{owner.available_minutes} min budget, needs "
                        f"{task.duration_minutes} min."
                    ),
                })
                continue

            # Conflict handling: place at the cursor so tasks never overlap.
            start = cursor
            if task.preferred_time is not None:
                start = max(cursor, task.preferred_time)

            scheduled.append({
                "pet": pet.name,
                "start": start,
                "clock": minutes_to_clock(start),
                "description": task.description,
                "duration": task.duration_minutes,
                "priority": task.priority,
                "reason": self._explain(task, start),
            })

            cursor = start + task.duration_minutes
            used += task.duration_minutes

        return scheduled, skipped

    def _sort_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Order tasks: highest priority first, then preferred time, then shorter."""
        return sorted(
            tasks,
            key=lambda t: (
                -t.priority_rank(),
                t.preferred_time if t.preferred_time is not None else 24 * 60,
                t.duration_minutes,
            ),
        )

    def _explain(self, task: Task, start: int) -> str:
        """Produce a short 'why this was scheduled here' reason."""
        if task.priority == "high":
            why = "High priority, placed early"
        elif task.priority == "low":
            why = "Low priority, filled in after the rest"
        else:
            why = "Medium priority"
        if task.preferred_time is not None and start != task.preferred_time:
            why += (
                f"; wanted {minutes_to_clock(task.preferred_time)}, "
                f"moved to {minutes_to_clock(start)} to avoid overlap"
            )
        elif task.preferred_time is not None:
            why += f"; honored preferred {minutes_to_clock(task.preferred_time)}"
        return why + "."
