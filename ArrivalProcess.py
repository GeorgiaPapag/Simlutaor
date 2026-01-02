import random
import simpy
from Customer import Customer

class ArrivalProcess:
    def __init__(self, env: simpy.Environment, config, customer_process, stats):
        self.env = env
        self.config = config
        self.customer_process = customer_process
        self.stats = stats
        self.customer_id = 0

    def get_interarrival_time(self) -> float:
        """Return next interarrival time based on peak / off-peak hours."""
        current_time = self.env.now % (24 * 60)

        if self.config.arrivals.PEAK_START <= current_time < self.config.arrivals.PEAK_END:
            mean = self.config.arrivals.PEAK_MEAN
        else:
            mean = self.config.arrivals.OFF_PEAK_MEAN

        return random.expovariate(1 / mean)

    def run(self):
        """SimPy process that generates arriving customers."""
        while True:
            interarrival = self.get_interarrival_time()
            yield self.env.timeout(interarrival)

            self.customer_id += 1
            self.stats.total_customers += 1

            is_seated = random.random() < self.config.consumption.SEATED_PROB

            customer = Customer(
                id=self.customer_id,
                arrival_time=self.env.now,
                is_seated=is_seated
            )

            self.env.process(self.customer_process.run(customer))
            print(f"{self.env.now:.2f} | Customer {customer.id} arrived")
