import numpy as np

class Stats:
    def __init__(self):
        self.total_customers = 0
        self.abandoned_customers = 0

        self.cashier_waits = []
        self.scooper_waits = []
        self.toppings_waits = []

        self.resource_busy_time = {
            "barista": 0.0,
            "scooper": 0.0,
            "cashier": 0.0,
            "waiter": 0.0,
            "toppings_staff": 0.0
        }

    # Add wait times
    # -------------------------
    def add_cashier_wait(self, t: float):
        self.cashier_waits.append(t)

    def add_scooper_wait(self, t: float):
        self.scooper_waits.append(t)

    # Percentiles
    # -------------------------
    def p95_cashier_wait(self):
        if not self.cashier_waits:
            return 0.0
        return np.percentile(self.cashier_waits, 95)

    def p95_scooper_wait(self):
        if not self.scooper_waits:
            return 0.0
        return np.percentile(self.scooper_waits, 95)
    
    def reset(self):
        """Reset all KPI-related statistics after warm-up."""
        self.total_customers = 0
        self.abandoned_customers = 0

        self.cashier_waits.clear()
        self.scooper_waits.clear()

        for k in self.resource_busy_time:
            self.resource_busy_time[k] = 0.0


