from ortools.sat.python import cp_model
from typing import List
from models.scheduling_model import Course, Instructor, Room, CourseAssignment

class AssignmentService:
    def __init__(self):
        self.model = cp_model.CpModel()

    def assign_courses(
        self,
        courses: List[Course],
        instructors: List[Instructor],
        rooms: List[Room]
    ) -> List[CourseAssignment]:
        instructor_vars = {
            (course.id, inst.id): self.model.NewBoolVar(f"assign_{course.id}_{inst.id}")
            for course in courses for inst in instructors
        }
        room_vars = {
            (course.id, room.id): self.model.NewBoolVar(f"room_{course.id}_{room.id}")
            for course in courses for room in rooms
        }

        # One instructor per course
        for course in courses:
            self.model.Add(sum(instructor_vars[(course.id, inst.id)] for inst in instructors) == 1)

        # One room per course
        for course in courses:
            self.model.Add(sum(room_vars[(course.id, room.id)] for room in rooms) == 1)

        # Simple objective: balance instructors
        self.model.Minimize(
            sum(instructor_vars[(course.id, inst.id)] for course in courses for inst in instructors)
        )

        solver = cp_model.CpSolver()
        solver.Solve(self.model)

        assignments = []
        for course in courses:
            for inst in instructors:
                if solver.BooleanValue(instructor_vars[(course.id, inst.id)]):
                    for room in rooms:
                        if solver.BooleanValue(room_vars[(course.id, room.id)]):
                            assignments.append(
                                CourseAssignment(
                                    course_id=course.id,
                                    instructor_id=inst.id,
                                    room_id=room.id
                                )
                            )
        return assignments
