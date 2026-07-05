"""PawPal+ Streamlit UI.

This is the "bridge" between the browser and the logic layer in
pawpal_system.py. Buttons here call real methods on the Owner / Pet / Task /
Scheduler classes, and the Owner instance is kept alive across reruns using
st.session_state.
"""

from datetime import time

import streamlit as st

# Step 1: bring the logic-layer classes into the UI.
from pawpal_system import Owner, Task, Scheduler, minutes_to_clock

PRIORITIES = ["high", "medium", "low"]
FREQUENCIES = ["daily", "weekly", "once"]
SPECIES = ["dog", "cat", "other"]


def minutes_to_time(minutes):
    """Turn minutes-from-midnight into a datetime.time for st.time_input."""
    return time(hour=(minutes // 60) % 24, minute=minutes % 60)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("A pet care planner. Add pets, add tasks, and generate today's schedule.")


# ---------------------------------------------------------------------------
# Step 2: application "memory".
#
# Streamlit re-runs this whole script on every interaction, so we must store the
# Owner in st.session_state — otherwise it would be re-created (empty) each time.
# We create it once, then reuse the same instance on every rerun.
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")

owner = st.session_state.owner


# ---------------------------------------------------------------------------
# Sidebar: owner-level settings (edited in place on the stored Owner)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Owner settings")
    owner.name = st.text_input("Owner name", value=owner.name)
    owner.available_minutes = st.number_input(
        "Daily time budget per pet (min)",
        min_value=15, max_value=600, value=owner.available_minutes, step=15,
    )
    start_hour = st.slider("Day starts at (hour)", 0, 23, owner.day_start // 60)
    owner.day_start = start_hour * 60
    st.caption(f"Care day begins at {minutes_to_clock(owner.day_start)}.")


# ---------------------------------------------------------------------------
# Step 3a: Add a pet  ->  owner.add_pet(...)
# ---------------------------------------------------------------------------
st.subheader("1. Add a pet")

with st.form("add_pet_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="")
    with col2:
        pet_species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        pet_breed = st.text_input("Breed (optional)", value="")

    if st.form_submit_button("Add pet"):
        if pet_name.strip():
            owner.add_pet(pet_name, species=pet_species, breed=pet_breed)
            st.success(f"Added {pet_name}!")
        else:
            st.error("Please enter a pet name.")

if not owner.pets:
    st.info("No pets yet. Add one above to get started.")
else:
    st.caption("Edit a pet's details or remove it — then regenerate for an updated plan.")
    for i, pet in enumerate(owner.pets):
        with st.expander(f"🐾 {pet.name} ({pet.species})"):
            # Edit form: change name / species / breed on the stored Pet in place.
            with st.form(f"edit_pet_{i}", clear_on_submit=False):
                e1, e2, e3 = st.columns(3)
                with e1:
                    new_name = st.text_input("Name", value=pet.name, key=f"pname_{i}")
                with e2:
                    species_idx = SPECIES.index(pet.species) if pet.species in SPECIES else 0
                    new_species = st.selectbox("Species", SPECIES, index=species_idx,
                                               key=f"pspec_{i}")
                with e3:
                    new_breed = st.text_input("Breed", value=pet.breed, key=f"pbreed_{i}")
                if st.form_submit_button("Save changes"):
                    try:
                        pet.update(name=new_name, species=new_species, breed=new_breed)
                        st.success(f"Updated {pet.name}.")
                        st.rerun()
                    except ValueError as err:
                        st.error(str(err))

            # Delete removes the pet and all of its tasks (cascade).
            if st.button(f"🗑️ Delete {pet.name}", key=f"pdel_{i}"):
                owner.remove_pet(pet)
                st.rerun()


# ---------------------------------------------------------------------------
# Step 3b: Add a task to a pet  ->  pet.add_task(Task(...))
# ---------------------------------------------------------------------------
st.subheader("2. Add a care task")

if not owner.pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
    # Checkbox lives OUTSIDE the form so toggling it reruns immediately and can
    # enable/disable the time field. Widgets inside a form don't rerun until submit.
    use_pref = st.checkbox("Set a preferred time")

    with st.form("add_task_form", clear_on_submit=True):
        pet_by_name = {p.name: p for p in owner.pets}
        target_name = st.selectbox("For which pet?", list(pet_by_name.keys()))

        c1, c2 = st.columns(2)
        with c1:
            description = st.text_input("Task", value="Morning walk")
            duration = st.number_input("Duration (min)", 1, 240, 30)
        with c2:
            priority = st.selectbox("Priority", ["high", "medium", "low"], index=1)
            frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])

        pref_time = st.time_input("Preferred time", disabled=not use_pref)

        if st.form_submit_button("Add task"):
            preferred_minutes = None
            if use_pref:
                preferred_minutes = pref_time.hour * 60 + pref_time.minute
            task = Task(
                description=description,
                duration_minutes=int(duration),
                priority=priority,
                frequency=frequency,
                preferred_time=preferred_minutes,
            )
            pet_by_name[target_name].add_task(task)
            st.success(f"Added '{description}' to {target_name}.")

    # Show the current tasks per pet, each editable / removable in place.
    for pi, pet in enumerate(owner.pets):
        if not pet.tasks:
            continue
        st.markdown(f"**{pet.name}'s tasks**")
        for ti, task in enumerate(pet.tasks):
            key = f"{pi}_{ti}"
            status = "✅ " if task.done else ""
            pref_label = (minutes_to_clock(task.preferred_time)
                          if task.preferred_time is not None else "no set time")
            with st.expander(
                f"{status}{task.description} · {task.priority} · {pref_label}"
            ):
                has_pref = task.preferred_time is not None
                # Checkbox outside the form so it can toggle the time field live.
                e_use_pref = st.checkbox("Set a preferred time", value=has_pref,
                                         key=f"tusep_{key}")
                with st.form(f"edit_task_{key}", clear_on_submit=False):
                    t1, t2 = st.columns(2)
                    with t1:
                        e_desc = st.text_input("Task", value=task.description,
                                               key=f"tdesc_{key}")
                        e_dur = st.number_input("Duration (min)", 1, 240,
                                                task.duration_minutes, key=f"tdur_{key}")
                    with t2:
                        e_pri = st.selectbox("Priority", PRIORITIES,
                                             index=PRIORITIES.index(task.priority),
                                             key=f"tpri_{key}")
                        e_freq = st.selectbox("Frequency", FREQUENCIES,
                                              index=FREQUENCIES.index(task.frequency),
                                              key=f"tfreq_{key}")
                    e_pref = st.time_input(
                        "Preferred time",
                        value=minutes_to_time(task.preferred_time) if has_pref else time(9, 0),
                        disabled=not e_use_pref, key=f"tpref_{key}",
                    )
                    if st.form_submit_button("Save changes"):
                        pref_minutes = (e_pref.hour * 60 + e_pref.minute
                                        if e_use_pref else None)
                        try:
                            task.update(
                                description=e_desc,
                                duration_minutes=int(e_dur),
                                priority=e_pri,
                                frequency=e_freq,
                                preferred_time=pref_minutes,
                            )
                            st.success("Task updated.")
                            st.rerun()
                        except ValueError as err:
                            st.error(str(err))

                b1, b2 = st.columns(2)
                with b1:
                    if st.button("🗑️ Delete task", key=f"tdel_{key}"):
                        pet.remove_task(task)
                        st.rerun()
                with b2:
                    if not task.done and st.button("✓ Mark complete", key=f"tdone_{key}"):
                        # Recurring tasks auto-spawn their next occurrence here.
                        pet.complete_task(task)
                        st.rerun()


# ---------------------------------------------------------------------------
# Step 3c: Generate today's schedule  ->  Scheduler().build_plan(owner)
# ---------------------------------------------------------------------------
st.subheader("3. Today's schedule")

scheduler = Scheduler()

# Conflict warnings surface as soon as two tasks share a time — shown live (before
# and after generating) so the owner can fix a clash they can't physically be in
# two places for.
conflicts = scheduler.detect_conflicts(owner)
if conflicts:
    st.warning("**⚠️ Scheduling conflicts detected:**\n\n"
               + "\n".join(f"- {c}" for c in conflicts))

if st.button("Generate schedule", type="primary", disabled=not owner.all_tasks()):
    st.session_state.plan = scheduler.build_plan(owner)

plan = st.session_state.get("plan")
if plan is not None:
    scheduled = plan["scheduled"]

    if not scheduled:
        st.warning("Nothing to schedule yet — add some tasks above.")
    else:
        if not plan["skipped"] and not conflicts:
            st.success(f"Planned {len(scheduled)} task(s) with no conflicts. 🎉")

        # Professional agenda: every pet's tasks merged and sorted chronologically.
        agenda = sorted(scheduled, key=lambda s: s["start"])
        st.table([
            {
                "Time": s["clock"],
                "Pet": s["pet"],
                "Task": s["description"],
                "Duration": f"{s['duration']} min",
                "Priority": s["priority"],
            }
            for s in agenda
        ])

        # Per-pet detail, including the scheduler's reasoning for each placement.
        for pet in owner.pets:
            items = [s for s in scheduled if s["pet"] == pet.name]
            if not items:
                continue
            st.markdown(f"### 🐾 {pet.name}")
            for s in items:
                st.markdown(
                    f"**{s['clock']}** — {s['description']} "
                    f"({s['duration']} min) · _{s['priority']}_"
                )
                st.caption(f"↳ {s['reason']}")

    if plan["skipped"]:
        st.markdown("#### ⚠️ Skipped (ran out of time)")
        for s in plan["skipped"]:
            st.caption(f"- {s['pet']}: {s['description']} — {s['reason']}")

    st.caption("Edited something above? Click **Generate schedule** again to refresh this plan.")

if not owner.all_tasks():
    st.caption("Add at least one task to enable scheduling.")
