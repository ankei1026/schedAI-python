from pydantic import BaseModel
from typing import List, Optional

class Room(BaseModel):
    id: str
    room_name: str
    room_type: str

class Course(BaseModel):
    id: str
    name: str
    units: int
    dept_id: str
    trimester_id: str
    academic_years_id: str

class Instructor(BaseModel):
    id: str
    user_id: str
    dept_id: str
    max_load: int = 12

class CourseAssignment(BaseModel):
    course_id: str
    instructor_id: str

class YearAndSection(BaseModel):
    year: int
    section: str

