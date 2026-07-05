# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

PawPal+ is built around three things a user should be able to do:

1. **Add a pet** — register a pet with basic info (name, species) so tasks have something to belong to.
2. **Add a care task** — attach a task like a walk, feeding, medication, or appointment to a pet, with a duration and priority.
3. **See today's tasks** — generate a daily plan that orders and prioritizes the tasks the user has added.

**a. Initial design**

My final design uses four classes, each with a clear responsibility:

- **Task** — a single care activity (description, duration, priority,
  frequency, completion status). Responsible for knowing its priority rank,
  whether it occurs on a given day, and marking itself complete.
- **Pet** — a single pet (name, species, breed) and the care tasks that belong
  to it. Responsible for holding and managing its own tasks (add/remove/list).
- **Owner** — the app user. Holds their name, daily time budget
  (`available_minutes`), and day start time, and owns a list of pets.
  Responsible for registering pets and exposing every task across all pets
  (`all_tasks()`).
- **Scheduler** — the "brain." Its one public method `build_plan` retrieves and
  organizes an owner's tasks into a daily schedule, one pet at a time. Each pet
  is its own lane (tasks placed back to back, no overlap), and pets run in
  parallel. Sorting and explanation are private helpers.

The relationships are simple: an Owner owns many Pets, a Pet has many Tasks, and
the Scheduler reads across all pets via `Owner.all_tasks()` — which keeps the
Scheduler decoupled from how the Owner stores its pets.

**b. Design changes**

My design changed significantly. I first brainstormed a richer **six-class
calendar model** (User, Pet, Task, Event, Calendar, Scheduler) where the
scheduler produced a first-draft plan and the user could freely drag events
around, with a `locked` flag protecting manual edits.

I then moved to the **four-class model above** for two reasons: the project's
design instructions specify four classes (Task, Pet, Owner, Scheduler), and the
simpler model is easier to build and test for this scope. Collapsing Event and
Calendar into the scheduler's output (a plain plan dictionary) removed a lot of
complexity while still supporting priority sorting, budget filtering, and
per-pet parallel lanes.

Two smaller changes along the way:

- I kept the **parallel-lane** multi-pet rule from the six-class design (each
  pet scheduled independently), which let me drop the overlap/conflict helper
  methods entirely.
- I renamed `Task.mark_done()` to `mark_complete()` so the public API matches
  the behavior tests and reads more clearly.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

My scheduler balances four constraints:

1. **Priority** — every task is `high`, `medium`, or `low`. `_sort_by_priority`
   orders each pet's tasks high → low so the most important care happens first.
2. **Time budget** — `Owner.available_minutes` caps how many minutes each pet's
   lane can hold. A task that doesn't fit is skipped (with a reason) rather than
   silently dropped.
3. **Preferred time** — if a task has a `preferred_time`, the planner honors it
   when possible, and otherwise pushes the task later (never earlier) so it
   doesn't overlap the task before it.
4. **No overlap within a pet** — tasks in one pet's lane are placed back to back;
   different pets run in parallel lanes, so two pets can share a time slot.

I decided **priority mattered most**, then the budget. A pet owner's
non-negotiables (medication, feeding) have to happen even on a tight day, so
priority sorts first; the time budget is the hard ceiling that decides what gets
cut; preferred time is a "nice to have" that yields whenever it would cause an
overlap. That ordering is encoded directly in the sort key
`(-priority_rank, preferred_time, duration)`.

**b. Tradeoffs**

My conflict detection makes a deliberate simplicity tradeoff: it only flags
tasks that share the **exact same preferred time**, not tasks whose *durations*
overlap. For example, a 30-minute walk at 08:00 and a feeding at 08:15 actually
collide in real life, but my `detect_conflicts()` won't warn about them because
their start times differ — it would only warn if both were set to 08:15.

This is reasonable for the scenario because a pet owner mostly sets round
"preferred times" (08:00, 09:00), so exact-match catches the common case, and
the logic stays tiny and easy to read (group tasks by time, warn on any group
with more than one task). It also can't crash — it returns a list of warning
strings, empty when there are no clashes. The scheduler still prevents *actual*
overlaps within a pet's lane by placing tasks back to back, so the un-detected
duration overlaps get pushed later rather than double-booked. If I had more
time, I'd upgrade the check to compare `[start, start + duration]` windows so it
catches overlapping durations too.

---

## 3. AI Collaboration

**a. How you used AI**

I used AI across every phase, but for different jobs: **design brainstorming**
early (comparing a six-class calendar model against the four-class model),
**automatic/agent editing** to scaffold the classes and later add full CRUD
across `pawpal_system.py` and `app.py` at once, **inline chat** for targeted
debugging, and **test generation** for the edge-case suite.

The most helpful prompts were the specific, code-grounded ones — attaching the
actual file and asking things like "what are the most important edge cases for a
pet scheduler with sorting and recurring tasks?" or "how should the Scheduler
retrieve all tasks from the Owner's pets?" Vague prompts gave generic answers;
pointing the assistant at real code made it reason about *my* system.

**b. Judgment and verification**

One moment I did not accept a suggestion as-is: when I added editing, the quick
path the assistant offered was to mutate a `Task`'s fields directly. I modified
that into a `Task.update()` method that re-runs validation and **rolls back** if
an edit would make the task invalid (empty description, zero duration). Direct
mutation was fewer lines but could leave a task in a broken state; the validated
version protects the class invariants that `__post_init__` already guarantees on
creation.

I verified AI suggestions two ways: the **CLI-first** workflow (`python main.py`)
let me eyeball the actual schedule output after every change, and the **pytest
suite** locked in behavior — when I wasn't sure whether a bug was in my test or my
logic, I ran the failing test in isolation and read the assertion against the
code. I trusted output I could reproduce, not explanations.

**c. AI strategy**

- **Most effective features:** agent/automatic editing for multi-file scaffolding
  and refactors (adding CRUD touched two files at once), and inline chat for
  surgical fixes — the clearest example was the `st.form` bug where the "Set a
  preferred time" checkbox looked broken; chat diagnosed that in-form widgets
  don't rerun until submit and I moved the checkbox outside the form.
- **A suggestion I rejected/modified:** for conflict detection, the "more complete"
  idea was to compare overlapping `[start, start+duration]` windows. I kept the
  simpler exact-preferred-time match instead (see 2b) because it's tiny, readable,
  and can't crash — a case where the more clever version wasn't worth the
  complexity for this scope. I documented the tradeoff rather than hiding it.
- **Separate chat sessions per phase:** keeping algorithm planning (Phase 4) in a
  different session from testing (Phase 5) kept each conversation focused. The
  testing session could concentrate purely on edge cases (empty pet, two tasks at
  the same time) without dragging along design debates, and I didn't have to
  re-explain context that had drifted.
- **Being the "lead architect":** the AI produced code fast, but I owned the
  decisions that shaped the system — choosing the four-class scope over six,
  recomputing the plan from scratch instead of caching it (so editing an input and
  regenerating is always correct, with no stale state), and picking readability
  over cleverness. My job wasn't to write every line; it was to set the "why,"
  guard the invariants, and verify with tests, while AI accelerated the "how."

---

## 4. Testing and Verification

**a. What you tested**

My suite (22 tests in `tests/test_pawpal.py`) covers every core behavior plus the
risky edge cases:

- **Sorting** — `sort_by_time()` returns chronological order and sends untimed
  tasks to the end of the day.
- **Recurrence** — completing a daily task spawns tomorrow's, a weekly task next
  week's (+7 days), and a once task nothing.
- **Conflict detection** — same-time tasks warn; different times, completed tasks,
  and untimed tasks do not.
- **Scheduling/packing** — tasks in a pet lane never overlap, high priority is
  placed first, and a task larger than the budget is skipped.
- **Edge cases** — empty owner, a pet with no tasks, and all-done pets plan
  without crashing.
- **Validation & CRUD** — invalid Task input is rejected; `update()` /
  `remove_pet()` edit and delete safely.

These mattered because they target the parts most likely to break silently: the
scheduling "brain" and the boundary cases (two tasks at the exact same time, a
pet with no tasks) that are easy to overlook by hand.

**b. Confidence**

I'm **4/5 confident**. Every core behavior and the main edge cases are covered and
green, and the CLI demo shows the same logic working end to end. I held back one
point because the tests exercise the logic layer only — the Streamlit UI wiring in
`app.py` is verified manually, not automatically.

If I had more time I'd test: a task pushed **past midnight** (the clock currently
wraps to `00:xx` with no warning), **re-completing an already-done task** (it can
spawn a duplicate next occurrence), **overlapping durations** rather than exact
time clashes, and behavior with a large number of tasks against a tiny budget.

---

## 5. Reflection

**a. What went well**

I'm most satisfied with two things. First, the scheduler **explains its
reasoning** — each scheduled task carries a short "why" ("High priority, placed
early; moved to 09:05 to avoid overlap"), which turns a plain list into something
a pet owner can actually trust. Second, the app lets a user **edit any input and
regenerate without refreshing the page**: because the plan is recomputed from
scratch and the data lives in `st.session_state`, changing a budget or a task time
just works, with no stale schedule to manage.

**b. What you would improve**

I'd upgrade conflict detection from exact-time matching to **overlapping-duration
windows** so a 30-minute 08:00 walk and an 08:15 feeding are flagged. I'd also
guard `complete_task` against **re-completing an already-done task** (today it can
create a duplicate next occurrence), handle schedules that **run past midnight**
more explicitly, and eventually **persist data** so pets and tasks survive a
browser restart.

**c. Key takeaway**

The biggest thing I learned is that being the **lead architect** matters more than
being a fast typist. AI can generate a lot of correct-looking code quickly, but the
value I added was in the decisions it can't own for me: scoping four classes
instead of six, choosing recompute-over-cache so edits stay correct, keeping
readable logic over "clever" one-liners, and insisting on validation and tests.
Small, testable increments plus CLI-first verification were what made
collaborating with a powerful AI reliable instead of risky.
