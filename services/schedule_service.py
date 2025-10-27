from typing import List
from datetime import datetime, timedelta
from .models.scheduling_model import Course, CourseAssignment


class ScheduleService:
    def __init__(self):
        pass

    def generate_weekly_timeslots(self, start_hour=7, end_hour=17):
        """Generate all 1-hour time slots Monday–Saturday (7AM–5PM)."""
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        timeslots = []
        for day in days:
            start = datetime.strptime(f"{start_hour}:00", "%H:%M")
            while start.hour < end_hour:
                end = start + timedelta(hours=1)
                timeslots.append({
                    "day": day,
                    "start": start.strftime("%H:%M"),
                    "end": end.strftime("%H:%M")
                })
                start = end
        return timeslots

    def generate_schedule(self, assignments: List[CourseAssignment], courses: List[Course]):
        """
        Sequentially assign classes Monday–Saturday, 7AM–5PM.
        Each course takes 'units' consecutive hours starting from earliest free slot.
        """
        timeslots = self.generate_weekly_timeslots(start_hour=7, end_hour=17)
        schedule = []
        slot_index = 0  # start from the first available time

        for assign in assignments:
            course = next((c for c in courses if c.id == assign.course_id), None)
            if not course:
                continue

            units = course.units  # 1 unit = 1 hour
            if slot_index + units > len(timeslots):
                raise ValueError("Not enough available time slots to schedule all courses.")

            # Get consecutive slots for this course
            start_slot = timeslots[slot_index]
            end_slot = timeslots[slot_index + units - 1]

            # Create formatted time range
            timeslot_str = f"{start_slot['day']}_{start_slot['start']}-{end_slot['end']}"

            schedule.append({
                "course_id": assign.course_id,
                "room_id": assign.room_id,
                "instructor_id": assign.instructor_id,
                "timeslot": timeslot_str
            })

            # Move to next available slot
            slot_index += units

        return schedule
