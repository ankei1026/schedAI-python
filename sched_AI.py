from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ortools.sat.python import cp_model
from collections import defaultdict
import math

app = FastAPI(title="Sched_AI")

# ----------------------------
# Default Configuration (user-editable)
# ----------------------------
default_sections = ["A", "B", "C", "D"]  # Blocks / Sections

# Subjects: tuple(subject_code, subject_title, duration_hours, needs_comlab_bool)
default_subjects = [
    ("CCP 1101", "Computer Programming 1", 3, True),
    ("CIC 1101", "Introduction to Computing", 3, True),
    ("CSP 1101", "Social and Professional Issues in Computing", 3, False),
    ("MLC 1101", "Literacy/Civic Welfare/Military Science 1", 3, False),
    ("PPE 1101", "Physical Education 1", 2, False),
    ("ZGE 1102", "The Contemporary World", 3, False),
    ("ZGE 1108", "Understanding the Self", 2, False),
]

# Rooms: classroom rooms (1..3) and two comlabs
default_room_names = ["Room 1", "Room 2", "Room 3", "Comlab 1", "Comlab 2"]
default_comlab_room_indices = [3, 4]  # indices in room_names which are comlabs

# Weekly schedule horizon
default_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
hours_per_day = 9  # 8:00 AM - 5:00 PM => 9 one-hour slots (8-9, 9-10, ..., 4-5)
start_hour = 8  # 8:00 AM

# ----------------------------
# Teachers (example data)
# ----------------------------
# Define teachers with name and department. Each teacher can teach specific subject codes.
default_teachers = [
    {"id": 0, "name": "Prof. Maria Santos", "department": "Computer Science", "can_teach": ["CCP 1101", "CIC 1101"]},
    {"id": 1, "name": "Dr. Jose Ramirez", "department": "Computer Science", "can_teach": ["CCP 1101", "CSP 1101"]},
    {"id": 2, "name": "Ms. Anna Cruz", "department": "General Education", "can_teach": ["ZGE 1102", "ZGE 1108"]},
    {"id": 3, "name": "Mr. Carlo Reyes", "department": "PE", "can_teach": ["PPE 1101"]},
    {"id": 4, "name": "Lt. Mark Dela Rosa", "department": "ROTC", "can_teach": ["MLC 1101"]},
]

# ----------------------------
# Request / response models
# ----------------------------
class SchedulerConfig(BaseModel):
    sections: Optional[List[str]] = None
    subjects: Optional[List[List]] = None  # list of tuples/lists: [code, title, duration, needs_lab]
    room_names: Optional[List[str]] = None
    comlab_room_indices: Optional[List[int]] = None
    days: Optional[List[str]] = None
    teachers: Optional[List[Dict[str, Any]]] = None
    hours_per_day: Optional[int] = None

# ----------------------------
# Helper functions
# ----------------------------
def slot_to_day_hour(slot: int, hours_per_day_local: int, start_hour_local: int):
    day = slot // hours_per_day_local
    hour_in_day = slot % hours_per_day_local
    hour = start_hour_local + hour_in_day
    return day, hour

def format_hour(h: int):
    suffix = "AM"
    display_hour = h
    if h == 12:
        suffix = "PM"
        display_hour = 12
    elif h == 0:
        display_hour = 12
        suffix = "AM"
    elif h > 12:
        display_hour = h - 12
        suffix = "PM"
    else:
        suffix = "AM"
    return f"{display_hour}:00 {suffix}"

def precheck_config(sections, subjects, room_names, comlab_room_indices, hours_per_day, days, teachers):
    num_days = len(days)
    H = hours_per_day * num_days
    errors = []
    per_section_total = sum(s[2] for s in subjects)
    weekly_hours = H
    if per_section_total > weekly_hours:
        errors.append(f"Each section requires {per_section_total} hours/week but only {weekly_hours} hours are available (per section).")

    total_lab_hours_needed = sum(s[2] for s in subjects if s[3]) * len(sections)
    lab_capacity = len(comlab_room_indices) * H
    if total_lab_hours_needed > lab_capacity:
        errors.append(f"Total lab hours required = {total_lab_hours_needed} but lab capacity = {lab_capacity} (comlabs * available slots).")

    nonlab_hours_needed = sum(s[2] for s in subjects if not s[3]) * len(sections)
    classroom_capacity = (len(room_names) - len(comlab_room_indices)) * H
    if nonlab_hours_needed > classroom_capacity:
        errors.append(f"Total classroom hours required for non-lab subjects = {nonlab_hours_needed} but classroom capacity = {classroom_capacity} (non-comlab rooms * available slots).")

    # Teacher coverage check: every subject must have at least one teacher who can teach it
    subject_codes = {s[0] for s in subjects}
    teacher_can = defaultdict(list)
    for t in teachers:
        for sc in t.get("can_teach", []):
            teacher_can[sc].append(t["name"])
    for sc in subject_codes:
        if sc not in teacher_can or len(teacher_can[sc]) == 0:
            errors.append(f"No teacher listed can teach subject {sc}. Add teachers or update 'can_teach' lists.")

    return errors

# ----------------------------
# Core scheduling runner
# ----------------------------
def build_and_solve(sections=default_sections,
                    subjects=default_subjects,
                    room_names=default_room_names,
                    comlab_room_indices=default_comlab_room_indices,
                    days=default_days,
                    teachers=default_teachers,
                    hours_per_day_local=hours_per_day,
                    start_hour_local=start_hour,
                    solver_time_limit_seconds=15):
    num_days = len(days)
    H = hours_per_day_local * num_days
    num_sections = len(sections)
    num_subjects = len(subjects)
    num_rooms = len(room_names)
    num_teachers = len(teachers)
    all_instances = [(sec_i, subj_i) for sec_i in range(num_sections) for subj_i in range(num_subjects)]

    # pre-check
    pre_errors = precheck_config(sections, subjects, room_names, comlab_room_indices, hours_per_day_local, days, teachers)
    if pre_errors:
        raise ValueError({"precheck_errors": pre_errors})

    model = cp_model.CpModel()

    # Variables
    starts = {}
    ends = {}
    intervals = {}
    assign_room = {}
    assign_teacher = {}

    for sec_i, subj_i in all_instances:
        dur = subjects[subj_i][2]
        max_start = H - dur
        starts[(sec_i, subj_i)] = model.new_int_var(0, max_start, f"start_s{sec_i}_sub{subj_i}")
        ends[(sec_i, subj_i)] = model.new_int_var(dur, H, f"end_s{sec_i}_sub{subj_i}")
        intervals[(sec_i, subj_i)] = model.new_interval_var(starts[(sec_i, subj_i)], dur, ends[(sec_i, subj_i)], f"iv_s{sec_i}_sub{subj_i}")
        for r in range(num_rooms):
            assign_room[(sec_i, subj_i, r)] = model.new_bool_var(f"assign_s{sec_i}_sub{subj_i}_r{r}")
        for t in range(num_teachers):
            assign_teacher[(sec_i, subj_i, t)] = model.new_bool_var(f"teach_s{sec_i}_sub{subj_i}_t{t}")

    # Room assignment: exactly one allowed room (respect labs)
    for sec_i, subj_i in all_instances:
        needs_lab = subjects[subj_i][3]
        if needs_lab:
            allowed_rooms = comlab_room_indices
        else:
            allowed_rooms = list(range(num_rooms))
        model.add(sum(assign_room[(sec_i, subj_i, r)] for r in allowed_rooms) == 1)

    # Teacher assignment: exactly one teacher able to teach this subject
    # Build map of teacher eligibility
    subject_code_to_idx = {subjects[i][0]: i for i in range(len(subjects))}
    for sec_i, subj_i in all_instances:
        scode = subjects[subj_i][0]
        eligible_teacher_indices = [t["id"] for t in teachers if scode in t.get("can_teach", [])]
        # if no eligible teachers, model would be infeasible; but precheck already checks this
        model.add(sum(assign_teacher[(sec_i, subj_i, t)] for t in eligible_teacher_indices) == 1)

    # Optional intervals per room to enforce no overlap
    opt_intervals_by_room = {r: [] for r in range(num_rooms)}
    for sec_i, subj_i in all_instances:
        dur = subjects[subj_i][2]
        for r in range(num_rooms):
            opt_iv = model.new_optional_interval_var(starts[(sec_i, subj_i)], dur, ends[(sec_i, subj_i)], assign_room[(sec_i, subj_i, r)], f"opt_iv_s{sec_i}_sub{subj_i}_r{r}")
            opt_intervals_by_room[r].append(opt_iv)

    for r in range(num_rooms):
        model.add_no_overlap(opt_intervals_by_room[r])

    # No overlap per section (a section cannot have two classes at the same time)
    intervals_by_section = {s: [] for s in range(num_sections)}
    for sec_i, subj_i in all_instances:
        intervals_by_section[sec_i].append(intervals[(sec_i, subj_i)])
    for s in range(num_sections):
        model.add_no_overlap(intervals_by_section[s])

    # No overlap per teacher (a teacher cannot teach two classes at the same time)
    opt_intervals_by_teacher = {t: [] for t in range(num_teachers)}
    for sec_i, subj_i in all_instances:
        dur = subjects[subj_i][2]
        for t in range(num_teachers):
            # optional interval present iff teacher assigned
            opt_iv = model.new_optional_interval_var(starts[(sec_i, subj_i)], dur, ends[(sec_i, subj_i)], assign_teacher[(sec_i, subj_i, t)], f"opt_iv_s{sec_i}_sub{subj_i}_t{t}")
            opt_intervals_by_teacher[t].append(opt_iv)
    for t in range(num_teachers):
        model.add_no_overlap(opt_intervals_by_teacher[t])

    # (Optional) If you want to forbid classes crossing day boundaries, you should restrict starts per day.
    # Current model allows crossing day boundary; to forbid it you'd need additional constraints.

    # Solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = solver_time_limit_seconds
    solver.parameters.num_search_workers = 8

    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"No feasible timetable found. Status: {status}")

    # Extract solution
    schedule_entries = []
    for sec_i, subj_i in all_instances:
        s_val = solver.Value(starts[(sec_i, subj_i)])
        dur = subjects[subj_i][2]
        e_val = s_val + dur
        assigned_room = None
        for r in range(num_rooms):
            if solver.Value(assign_room[(sec_i, subj_i, r)]) == 1:
                assigned_room = r
                break
        assigned_teacher = None
        for t in range(num_teachers):
            if solver.Value(assign_teacher[(sec_i, subj_i, t)]) == 1:
                assigned_teacher = t
                break
        if assigned_room is None:
            raise RuntimeError(f"Instance sec{sec_i} subj{subj_i} had no room assigned in solution.")
        if assigned_teacher is None:
            raise RuntimeError(f"Instance sec{sec_i} subj{subj_i} had no teacher assigned in solution.")
        day_idx, start_hr = slot_to_day_hour(s_val, hours_per_day_local, start_hour_local)
        end_day_idx, end_hr = slot_to_day_hour(e_val - 1, hours_per_day_local, start_hour_local)
        schedule_entries.append({
            "section": sections[sec_i],
            "subject_code": subjects[subj_i][0],
            "subject_title": subjects[subj_i][1],
            "start_slot": s_val,
            "end_slot_exclusive": e_val,
            "start_day": day_idx,
            "end_day": end_day_idx,
            "start_hour": start_hr,
            "end_hour_exclusive": start_hr + dur,
            "room": room_names[assigned_room],
            "duration": dur,
            "teacher_id": assigned_teacher,
            "teacher_name": next((t["name"] for t in teachers if t["id"] == assigned_teacher), None),
        })

    # Build per-day view
    per_day_entries = {d_idx: [] for d_idx in range(num_days)}
    for ent in schedule_entries:
        s_slot = ent["start_slot"]
        e_slot = ent["end_slot_exclusive"]
        cur = s_slot
        while cur < e_slot:
            day_idx = cur // hours_per_day_local
            run_start = cur
            day_end_slot = (day_idx + 1) * hours_per_day_local
            run_end = min(e_slot, day_end_slot)
            start_hr = start_hour_local + (run_start % hours_per_day_local)
            end_hr = start_hour_local + ((run_end - 1) % hours_per_day_local) + 1
            per_day_entries[day_idx].append({
                "start_slot": run_start,
                "start_hour": start_hr,
                "end_hour": end_hr,
                "section": ent["section"],
                "subject_code": ent["subject_code"],
                "subject_title": ent["subject_title"],
                "room": ent["room"],
                "duration": run_end - run_start,
                "teacher_name": ent["teacher_name"],
            })
            cur = run_end

    for d_idx in per_day_entries:
        per_day_entries[d_idx].sort(key=lambda x: x["start_slot"])

    # Also produce per-section compact view
    per_section = {sec: [] for sec in sections}
    for ent in schedule_entries:
        per_section[ent["section"]].append(ent)

    result = {
        "meta": {
            "sections": sections,
            "days": days,
            "hours_per_day": hours_per_day_local,
            "start_hour": start_hour_local,
            "room_names": room_names,
            "teachers": teachers,
        },
        "schedule_entries": schedule_entries,
        "per_day_entries": per_day_entries,
        "per_section": per_section,
    }
    return result

# ----------------------------
# FastAPI endpoints
# ----------------------------
@app.post("/schedule")
def post_schedule(config: Optional[SchedulerConfig] = None):
    """
    POST /schedule
    Optionally send JSON body with any of:
    {
      "sections": ["A","B"],
      "subjects": [["CCP 1101","Computer Programming 1",3,true], ...],
      "room_names": ["Room 1", "Comlab 1"],
      "comlab_room_indices": [1],
      "days": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
      "teachers": [{"id":0,"name":"Prof X","department":"CS","can_teach":["CCP 1101"]}, ...],
      "hours_per_day": 9
    }
    If no body supplied, default built-in config is used.
    """
    try:
        if config:
            sections = config.sections if config.sections is not None else default_sections
            subjects = [tuple(s) for s in config.subjects] if config.subjects is not None else default_subjects
            room_names = config.room_names if config.room_names is not None else default_room_names
            comlab_room_indices = config.comlab_room_indices if config.comlab_room_indices is not None else default_comlab_room_indices
            days = config.days if config.days is not None else default_days
            teachers = config.teachers if config.teachers is not None else default_teachers
            hours_pd = config.hours_per_day if config.hours_per_day is not None else hours_per_day
        else:
            sections = default_sections
            subjects = default_subjects
            room_names = default_room_names
            comlab_room_indices = default_comlab_room_indices
            days = default_days
            teachers = default_teachers
            hours_pd = hours_per_day

        # Build & solve
        result = build_and_solve(sections=sections,
                                 subjects=subjects,
                                 room_names=room_names,
                                 comlab_room_indices=comlab_room_indices,
                                 days=days,
                                 teachers=teachers,
                                 hours_per_day_local=hours_pd,
                                 start_hour_local=start_hour,
                                 solver_time_limit_seconds=15)
        return result
    except ValueError as ve:
        # precheck errors
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/schedule")
def get_schedule():
    """
    GET /schedule
    Runs the scheduler with default built-in configuration and returns JSON result.
    """
    return post_schedule(None)

# ----------------------------
# If run directly, print a human-friendly timetable to console as well
# ----------------------------
if __name__ == "__main__":
    import json, sys
    try:
        result = build_and_solve()
    except ValueError as ve:
        print("Precheck failed:", ve)
        sys.exit(1)
    except Exception as e:
        print("Error while solving:", e)
        sys.exit(1)

    days = result["meta"]["days"]
    per_day = result["per_day_entries"]
    print("\nWEEKLY TIMETABLE (Monday - Friday):\n")
    for d_idx, day_name in enumerate(days):
        print(day_name)
        if not per_day[d_idx]:
            print("  (no classes)")
        else:
            for e in per_day[d_idx]:
                start_label = format_hour(e["start_hour"])
                end_label = format_hour(e["end_hour"])
                print(f"  {start_label} - {end_label}, {e['subject_code']} {e['subject_title']}, Block {e['section']}, {e['room']}, Teacher: {e['teacher_name']}")
        print()

    print("PER-SECTION SUMMARY:\n")
    for sec, entries in result["per_section"].items():
        print(f"Block {sec}:")
        entries.sort(key=lambda x: x["start_slot"])
        for e in entries:
            day_idx = e["start_day"]
            s_hr = e["start_hour"]
            end_slot = e["end_slot_exclusive"]
            end_day, end_hour_tmp = slot_to_day_hour(end_slot - 1, hours_per_day, start_hour)
            end_hr = end_hour_tmp + 1
            print(f"  {days[day_idx]} {format_hour(s_hr)} - {format_hour(end_hr)}, {e['subject_code']} {e['subject_title']}, Room: {e['room']}, Teacher: {e['teacher_name']}")
        print()
