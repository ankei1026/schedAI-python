from ortools.sat.python import cp_model

class ScheduleSolver:
    """Encapsulates the OR-Tools constraint model."""

    def __init__(self, config):
        self.config = config
        self.model = cp_model.CpModel()

    def build_model(self):
        # Build variables, constraints, etc.
        # (You can reuse your build_and_solve logic here)
        pass

    def solve(self):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15
        solver.parameters.num_search_workers = 8

        status = solver.solve(self.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError("No feasible schedule found.")
        return solver
