from fastapi import APIRouter, HTTPException
from .models import SchedulerConfig
from .validator import ConfigValidator
from .solver import ScheduleSolver
from .formatter import ScheduleFormatter

router = APIRouter()

@router.post("/schedule")
def generate_schedule(config: SchedulerConfig):
    validator = ConfigValidator(config)
    errors = validator.validate()
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    solver = ScheduleSolver(config)
    solver.build_model()
    result = solver.solve()

    formatted = ScheduleFormatter(config, result).to_json(result)
    return formatted
