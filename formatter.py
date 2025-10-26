class ScheduleFormatter:
    """Handles transforming solver output into JSON or printable format."""

    def __init__(self, config, solver):
        self.config = config
        self.solver = solver

    def to_json(self, solution_data):
        # Convert solver output into structured JSON
        return {"schedule": solution_data}
