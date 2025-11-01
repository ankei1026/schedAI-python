# app/services/AssignScheduling.py
from ortools.sat.python import cp_model
from typing import List
from models.scheduling_model import Course, Instructor, CourseAssignment


class AssignmentService:
    def __init__(self):
        self.model = cp_model.CpModel()

    def assign_courses(self, courses: List[Course], instructors: List[Instructor]) -> List[CourseAssignment]:
        # ✅ Deduplicate instructors by user_id safely
        unique_instructors = {}
        for inst in instructors:
            user_key = getattr(inst, "user_id", None)
            if user_key is None:
                # fallback: use instructor.id if user_id is missing
                user_key = inst.id
            # Only keep the first instructor per user_id
            if user_key not in unique_instructors:
                unique_instructors[user_key] = inst

        # Replace with unique list
        instructors = list(unique_instructors.values())

        # ✅ Group instructors by department
        dept_instructors = {}
        for inst in instructors:
            dept_instructors.setdefault(inst.dept_id, []).append(inst)

        assignments = []

        for dept_id, dept_courses in self._group_courses_by_dept(courses).items():
            if dept_id not in dept_instructors:
                continue  # no instructors in this department

            insts = dept_instructors[dept_id]
            print(f"Assigning {len(dept_courses)} courses for dept {dept_id} to {len(insts)} instructors")

            assignments.extend(self._assign_department_courses(dept_courses, insts))

        return assignments

    def _group_courses_by_dept(self, courses: List[Course]):
        grouped = {}
        for c in courses:
            grouped.setdefault(c.dept_id, []).append(c)
        return grouped

    def _assign_department_courses(self, courses: List[Course], instructors: List[Instructor]):
        model = cp_model.CpModel()

        # Binary variables: assign_{course.id}_{inst.id}
        assign_vars = {
            (c.id, i.id): model.NewBoolVar(f"assign_{c.id}_{i.id}")
            for c in courses for i in instructors
        }

        # Each course must be assigned to exactly one instructor
        for c in courses:
            model.Add(sum(assign_vars[(c.id, i.id)] for i in instructors) == 1)

        # Compute total units per instructor
        total_units = {}
        for i in instructors:
            total_units[i.id] = model.NewIntVar(0, sum(c.units for c in courses), f"total_units_{i.id}")
            model.Add(total_units[i.id] == sum(assign_vars[(c.id, i.id)] * c.units for c in courses))

        # Balance loads: minimize max load difference
        max_load = model.NewIntVar(0, 100, "max_load")
        min_load = model.NewIntVar(0, 100, "min_load")
        for t in total_units.values():
            model.Add(t <= max_load)
            model.Add(t >= min_load)

        model.Minimize(max_load - min_load)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5
        solver.Solve(model)

        assignments = []
        for c in courses:
            for i in instructors:
                if solver.BooleanValue(assign_vars[(c.id, i.id)]):
                    assignments.append(CourseAssignment(course_id=c.id, instructor_id=i.id))
        return assignments
