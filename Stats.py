class Stats:
    def __init__(self):
        self.total_customers = 0
        self.abandoned_customers = 0

        self.cashier_waits = []
        self.scooper_waits = []

        self.resource_busy_time = {
            "barista": 0.0,
            "scooper": 0.0,
            "cashier": 0.0,
            "waiter": 0.0,
        }
