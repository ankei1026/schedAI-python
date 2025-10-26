from collections import defaultdict

class ConfigValidator:
    """Handles all pre-checks before solving the schedule."""

    def __init__(self, config):
        self.config = config

    def validate(self):
        errors = []
        total_hours = len(self.config.days) * self.config.hours_per_day
        subjects = self.config.subjects

        # Per-section load
        per_section_total = sum(s.duration for s in subjects)
        if per_section_total > total_hours:
            errors.append(f"Each section needs {per_section_total} hrs/week but only {total_hours} hrs available.")

        # Lab capacity
        total_lab = sum(s.duration for s in subjects if s.needs_lab) * len(self.config.sections)
        lab_capacity = len(self.config.comlab_indices) * total_hours
        if total_lab > lab_capacity:
            errors.append(f"Total lab hrs {total_lab} > capacity {lab_capacity}.")

        # Non-lab capacity
        total_nonlab = sum(s.duration for s in subjects if not s.needs_lab) * len(self.config.sections)
        nonlab_capacity = (len(self.config.rooms) - len(self.config.comlab_indices)) * total_hours
        if total_nonlab > nonlab_capacity:
            errors.append(f"Total classroom hrs {total_nonlab} > capacity {nonlab_capacity}.")

        # Teacher coverage
        teacher_map = defaultdict(list)
        for t in self.config.teachers:
            for sub in t.can_teach:
                teacher_map[sub].append(t.name)
        for s in subjects:
            if not teacher_map.get(s.code):
                errors.append(f"No teacher can teach {s.code}")

        return errors
