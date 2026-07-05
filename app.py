"""PawPal+ Streamlit UI.

This is the "bridge" between the browser and the logic layer in
pawpal_system.py. Buttons here call real methods on the Owner / Pet / Task /
Scheduler classes, and the Owner instance is kept alive across reruns using
st.session_state.
"""

import streamlit as st

# Step 1: bring the logic-layer classes into the UI.
from pawpal_system import Owner, Task, Scheduler, minutes_to_clock

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

if owner.pets:
    st.write("Your pets:", ", ".join(f"{p.name} ({p.species})" for p in owner.pets))
else:
    st.info("No pets yet. Add one above to get started.")


# ---------------------------------------------------------------------------
# Step 3b: Add a task to a pet  ->  pet.add_task(Task(...))
# ---------------------------------------------------------------------------
st.subheader("2. Add a care task")

if not owner.pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
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

        use_pref = st.checkbox("Set a preferred time")
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

    # Show the current tasks per pet so the user sees what's stored.
    for pet in owner.pets:
        if pet.tasks:
            st.markdown(f"**{pet.name}'s tasks**")
            st.table([
                {
                    "task": t.description,
                    "duration": t.duration_minutes,
                    "priority": t.priority,
                    "frequency": t.frequency,
                    "preferred": minutes_to_clock(t.preferred_time)
                    if t.preferred_time is not None else "—",
                    "done": "✅" if t.done else "",
                }
                for t in pet.tasks
            ])


# ---------------------------------------------------------------------------
# Step 3c: Generate today's schedule  ->  Scheduler().build_plan(owner)
# ---------------------------------------------------------------------------
st.subheader("3. Today's schedule")

if st.button("Generate schedule", type="primary", disabled=not owner.all_tasks()):
    plan = Scheduler().build_plan(owner)

    if not plan["scheduled"]:
        st.warning("Nothing to schedule yet — add some tasks above.")

    for pet in owner.pets:
        items = [s for s in plan["scheduled"] if s["pet"] == pet.name]
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

if not owner.all_tasks():
    st.caption("Add at least one task to enable scheduling.")
