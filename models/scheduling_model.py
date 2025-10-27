from pydantic import BaseModel
from typing import List, Optional

class Room(BaseModel):
    id: str
    room_name: str
    room_type: str

class Instructor(BaseModel):
    id: str
    user_id: str
    dept_id: str

class Course(BaseModel):
    id: str
    code: str
    name: str
    units: int
    dept_id: str
    trimester_id: Optional[str]
    academic_years_id: str
    has_lab: bool
    is_assigned: bool

class CourseAssignment(BaseModel):
    course_id: str
    instructor_id: str
    room_id: str

class YearAndSection(BaseModel):
    year: int
    section: str

