from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple

class Subject(BaseModel):
    code: str
    title: str
    duration: int
    needs_lab: bool

class Teacher(BaseModel):
    id: int
    name: str
    department: str
    can_teach: List[str]

class SchedulerConfig(BaseModel):
    sections: List[str]
    subjects: List[Subject]
    rooms: List[str]
    comlab_indices: List[int]
    days: List[str]
    hours_per_day: int
    teachers: List[Teacher]
    start_hour: int = 8
