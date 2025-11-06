from models.scheduling_model import ScheduleData, ConflictRequest
from datetime import datetime

def parse_time(t: str) -> datetime:
    """Parse time in either HH:MM or HH:MM:SS format."""
    try:
        return datetime.strptime(t, "%H:%M:%S")
    except ValueError:
        return datetime.strptime(t, "%H:%M")

def format_time_ampm(time_str: str) -> str:
    """Convert 24-hour time format to 12-hour AM/PM format."""
    try:
        # Parse the time
        time_obj = parse_time(time_str)
        # Format to AM/PM
        return time_obj.strftime("%I:%M %p").lstrip('0')
    except ValueError:
        return time_str  # Return original if parsing fails

def check_schedule_conflict_logic(request: ConflictRequest) -> dict:
    """Check if the new schedule conflicts with existing ones."""
    new = request.new_schedule
    
    # Define lunch break time range
    lunch_start = parse_time("12:00")
    lunch_end = parse_time("13:00")
    
    start_new = parse_time(new.start_time)
    end_new = parse_time(new.end_time)
    
    # Check lunch break conflict for new schedule
    lunch_overlap = start_new < lunch_end and end_new > lunch_start
    if lunch_overlap:
        return {
            "conflict": True,
            "type": "lunch_break",
            "message": "Lunch Break: Students needs to rest and eat lunch for energy (12:00 PM - 1:00 PM)."
        }

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

        # Parse time ranges safely
        start_exist = parse_time(existing.start_time)
        end_exist = parse_time(existing.end_time)

        # Check for time overlap
        overlap = start_new < end_exist and end_new > start_exist

        if overlap:
            # Format date and time for conflict message with AM/PM
            conflict_days = ", ".join(overlapping_days)
            conflict_time = f"{format_time_ampm(existing.start_time)}-{format_time_ampm(existing.end_time)}"
            
            # Use instructor name or fallback to ID
            instructor_display_name = existing.instructor_name or f"Instructor {existing.instructor_id}"
            # Use room name or fallback to ID
            room_display_name = existing.room_name or f"Room {existing.room_id}"
            
            # Room conflict
            if existing.room_id == new.room_id:
                return {
                    "conflict": True,
                    "type": "room",
                    "message": f"Room Conflict: The selected room {room_display_name} is already occupied on {conflict_days} {conflict_time}.",
                    "conflicting_instructor_id": existing.instructor_id,
                    "conflicting_instructor_name": existing.instructor_name,
                    "conflicting_room_id": existing.room_id,
                    "conflicting_room_name": existing.room_name,
                    "days": list(overlapping_days),
                    "time": conflict_time
                }

            # Instructor conflict
            if existing.instructor_id == new.instructor_id:
                return {
                    "conflict": True,
                    "type": "instructor",
                    "message": f"Instructor Conflict: {instructor_display_name} has schedule on {conflict_days} at {conflict_time}",
                    "conflicting_instructor_id": existing.instructor_id,
                    "conflicting_instructor_name": existing.instructor_name,
                    "days": list(overlapping_days),
                    "time": conflict_time
                }

    # No conflict found
    return {"conflict": False, "message": "No conflicts detected."}