from models.scheduling_model import ScheduleData, ConflictRequest
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

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

def format_suggestions_message(vacant_slots: List[Dict]) -> str:
    """Format vacant slots into a readable message."""
    if not vacant_slots:
        return ""
    
    messages = []
    for day_slot in vacant_slots:
        day = day_slot['day']
        slots = day_slot['slots']
        
        if slots:
            slot_strings = [f"{slot['start']}-{slot['end']}" for slot in slots]
            messages.append(f"{day}: {', '.join(slot_strings)}")
    
    if messages:
        return "Available time slots: " + ", ".join(messages)
    return ""

def get_vacant_slots(occupied_slots: List[Tuple[datetime, datetime]], day_start: datetime, day_end: datetime, lunch_start: datetime, lunch_end: datetime) -> List[Dict]:
    """Find vacant time slots between occupied periods."""
    vacant_slots = []
    
    # Sort occupied slots by start time
    occupied_slots.sort(key=lambda x: x[0])
    
    # Check before first occupied slot
    first_occupied_start = occupied_slots[0][0] if occupied_slots else day_end
    if day_start < first_occupied_start:
        vacant_slots.append({
            "start": format_time_ampm(day_start.strftime("%H:%M")),
            "end": format_time_ampm(first_occupied_start.strftime("%H:%M"))
        })
    
    # Check between occupied slots and around lunch
    for i in range(len(occupied_slots) - 1):
        current_end = occupied_slots[i][1]
        next_start = occupied_slots[i + 1][0]
        
        # Skip if slots are back-to-back
        if current_end >= next_start:
            continue
            
        # Check if lunch break falls between these slots
        if current_end <= lunch_start and next_start >= lunch_end:
            # Time before lunch
            if current_end < lunch_start:
                vacant_slots.append({
                    "start": format_time_ampm(current_end.strftime("%H:%M")),
                    "end": format_time_ampm(lunch_start.strftime("%H:%M"))
                })
            # Time after lunch
            if lunch_end < next_start:
                vacant_slots.append({
                    "start": format_time_ampm(lunch_end.strftime("%H:%M")),
                    "end": format_time_ampm(next_start.strftime("%H:%M"))
                })
        else:
            # Regular gap between classes
            if current_end < next_start:
                vacant_slots.append({
                    "start": format_time_ampm(current_end.strftime("%H:%M")),
                    "end": format_time_ampm(next_start.strftime("%H:%M"))
                })
    
    # Check after last occupied slot
    if occupied_slots:
        last_occupied_end = occupied_slots[-1][1]
        if last_occupied_end < day_end:
            vacant_slots.append({
                "start": format_time_ampm(last_occupied_end.strftime("%H:%M")),
                "end": format_time_ampm(day_end.strftime("%H:%M"))
            })
    else:
        # No occupied slots - entire day is vacant (except lunch)
        vacant_slots.append({
            "start": format_time_ampm(day_start.strftime("%H:%M")),
            "end": format_time_ampm(lunch_start.strftime("%H:%M"))
        })
        vacant_slots.append({
            "start": format_time_ampm(lunch_end.strftime("%H:%M")),
            "end": format_time_ampm(day_end.strftime("%H:%M"))
        })
    
    return vacant_slots

def check_schedule_conflict_logic(request: ConflictRequest) -> dict:
    """Check if the new schedule conflicts with existing ones."""
    new = request.new_schedule
    
    # Define school operating hours
    school_start = parse_time("06:00")
    school_end = parse_time("21:00")
    
    # Define lunch break time range
    lunch_start = parse_time("12:00")
    lunch_end = parse_time("13:00")
    
    start_new = parse_time(new.start_time)
    end_new = parse_time(new.end_time)
    
    # Check if schedule is outside school hours
    if start_new < school_start or end_new > school_end:
        return {
            "conflict": True,
            "type": "school_hours",
            "message": f"School Hours Violation: Classes must be scheduled between {format_time_ampm('06:00')} and {format_time_ampm('21:00')} only.",
            "suggestions": ""
        }
    
    # Check lunch break conflict for new schedule
    lunch_overlap = start_new < lunch_end and end_new > lunch_start
    if lunch_overlap:
        return {
            "conflict": True,
            "type": "lunch_break",
            "message": "Lunch Break: Students needs to rest and eat lunch for energy (12:00 PM - 1:00 PM).",
            "suggestions": ""
        }

    # Group existing schedules by room and day for vacancy suggestions
    room_schedules_by_day = {}
    instructor_schedules_by_day = {}
    
    for existing in request.existing_schedules:
        # Only consider same academic year and trimester
        if not (existing.academic_year_id == new.academic_year_id and existing.trimester_id == new.trimester_id):
            continue
            
        # Group by room and day
        if existing.room_id not in room_schedules_by_day:
            room_schedules_by_day[existing.room_id] = {}
        
        # Group by instructor and day  
        if existing.instructor_id not in instructor_schedules_by_day:
            instructor_schedules_by_day[existing.instructor_id] = {}
            
        for day in existing.days:
            # Initialize day if not exists
            if day not in room_schedules_by_day[existing.room_id]:
                room_schedules_by_day[existing.room_id][day] = []
            if day not in instructor_schedules_by_day[existing.instructor_id]:
                instructor_schedules_by_day[existing.instructor_id][day] = []
                
            # Add schedule time slots
            room_schedules_by_day[existing.room_id][day].append(
                (parse_time(existing.start_time), parse_time(existing.end_time))
            )
            instructor_schedules_by_day[existing.instructor_id][day].append(
                (parse_time(existing.start_time), parse_time(existing.end_time))
            )

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
                # Get vacant slots for this room on conflict days
                vacant_slots = []
                for day in overlapping_days:
                    if (existing.room_id in room_schedules_by_day and 
                        day in room_schedules_by_day[existing.room_id]):
                        
                        day_vacant_slots = get_vacant_slots(
                            room_schedules_by_day[existing.room_id][day],
                            school_start, school_end, lunch_start, lunch_end
                        )
                        if day_vacant_slots:
                            vacant_slots.append({
                                "day": day,
                                "slots": day_vacant_slots
                            })
                
                # Create SEPARATE messages
                conflict_message = f"Room Conflict: The selected room {room_display_name} is already occupied on {conflict_days} {conflict_time}."
                suggestions_message = format_suggestions_message(vacant_slots)
                
                return {
                    "conflict": True,
                    "type": "room",
                    "message": conflict_message,  # Main conflict message
                    "suggestions": suggestions_message,  # Separate suggestions message
                    "conflicting_instructor_id": existing.instructor_id,
                    "conflicting_instructor_name": existing.instructor_name,
                    "conflicting_room_id": existing.room_id,
                    "conflicting_room_name": existing.room_name,
                    "days": list(overlapping_days),
                    "time": conflict_time,
                    "vacant_slots": vacant_slots if vacant_slots else None
                }

            # Instructor conflict
            if existing.instructor_id == new.instructor_id:
                # Get vacant slots for this instructor on conflict days
                vacant_slots = []
                for day in overlapping_days:
                    if (existing.instructor_id in instructor_schedules_by_day and 
                        day in instructor_schedules_by_day[existing.instructor_id]):
                        
                        day_vacant_slots = get_vacant_slots(
                            instructor_schedules_by_day[existing.instructor_id][day],
                            school_start, school_end, lunch_start, lunch_end
                        )
                        if day_vacant_slots:
                            vacant_slots.append({
                                "day": day,
                                "slots": day_vacant_slots
                            })
                
                # Create SEPARATE messages
                conflict_message = f"Instructor Conflict: {instructor_display_name} has schedule on {conflict_days} at {conflict_time}"
                suggestions_message = format_suggestions_message(vacant_slots)
                
                return {
                    "conflict": True,
                    "type": "instructor",
                    "message": conflict_message,  # Main conflict message
                    "suggestions": suggestions_message,  # Separate suggestions message
                    "conflicting_instructor_id": existing.instructor_id,
                    "conflicting_instructor_name": existing.instructor_name,
                    "days": list(overlapping_days),
                    "time": conflict_time,
                    "vacant_slots": vacant_slots if vacant_slots else None
                }

    # No conflict found
    return {
        "conflict": False, 
        "message": "No conflicts detected.",
        "suggestions": ""
    }