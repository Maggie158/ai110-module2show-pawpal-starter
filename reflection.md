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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

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

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
