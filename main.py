from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.assignment_service import AssignmentService
from models.scheduling_model import Course, Instructor, Room, CourseAssignment
from services.conflict_service import ConflictRequest, check_schedule_conflict_logic
from models.scheduling_model import ScheduleData, ConflictRequest
from pydantic import BaseModel
from typing import List

#  python -m uvicorn main:app --reload --port 9000 run this
app = FastAPI(title="Sched_AI")

# --- Allow Laravel access ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://127.0.0.1:8000"] for Laravel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "FastAPI is running!"}

class AssignmentRequest(BaseModel):
    courses: List[Course]
    instructors: List[Instructor]

@app.post("/assign-courses")
def assign_courses(courses: List[Course], instructors: List[Instructor]):
    service = AssignmentService()
    assignments = service.assign_courses(courses, instructors)

    return {
        "recommended_instructors": [
            {"id": a.instructor_id, "course_id": a.course_id} for a in assignments
        ]
    }

# --- Request body model ---
class ScheduleRequest(BaseModel):
    assignments: List[CourseAssignment]
    timeslots: List[str]

# --- Endpoint ---
@app.post("/scheduling")
def generate_schedule(data: ScheduleRequest):
    """
    Generate a weekly class schedule based on course assignments and available time slots.
    """
    service = ScheduleService()
    schedule = service.generate_schedule(
        assignments=data.assignments,
        timeslots=data.timeslots
    )
    return {"schedule": schedule}

@app.post("/check_schedule_conflict")
def check_schedule_conflict(request: ConflictRequest):
    """
    Delegates conflict checking to conflict_service.py
    """
    result = check_schedule_conflict_logic(request)
    return result
