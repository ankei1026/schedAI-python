from models.scheduling_model import ScheduleData, ConflictRequest
from datetime import datetime

def parse_time(t: str) -> datetime:
    """Parse time in either HH:MM or HH:MM:SS format."""
    try:
        return datetime.strptime(t, "%H:%M:%S")
    except ValueError:
        return datetime.strptime(t, "%H:%M")

def check_schedule_conflict_logic(request: ConflictRequest) -> dict:
    """Check if the new schedule conflicts with existing ones."""
    new = request.new_schedule

    for existing in request.existing_schedules:
        # Check if they belong to the same academic year and trimester
        if not (
            existing.academic_year_id == new.academic_year_id
            and existing.trimester_id == new.trimester_id
        ):
            continue

        # Check overlapping days
        overlapping_days = set(existing.days) & set(new.days)
        if not overlapping_days:
            continue

        # ✅ Parse time ranges safely
        start_new = parse_time(new.start_time)
        end_new = parse_time(new.end_time)
        start_exist = parse_time(existing.start_time)
        end_exist = parse_time(existing.end_time)

        # Check for time overlap
        overlap = start_new < end_exist and end_new > start_exist

        if overlap:
            # ✅ Room conflict
            if existing.room_id == new.room_id:
                return {
                    "conflict": True,
                    "type": "room",
                    "message": (
                        f"Room conflict on {', '.join(overlapping_days)} "
                        f"({existing.start_time}-{existing.end_time})."
                    ),
                }

            # ✅ Instructor conflict
            if existing.instructor_id == new.instructor_id:
                return {
                    "conflict": True,
                    "type": "instructor",
                    "message": (
                        f"Instructor conflict on {', '.join(overlapping_days)} "
                        f"({existing.start_time}-{existing.end_time})."
                    ),
                }

    # ✅ No conflict found
    return {"conflict": False, "message": "No conflicts detected."}
