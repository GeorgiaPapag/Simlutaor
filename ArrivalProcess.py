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

        self.store_open = self.env.event()
        self.store_open.succeed()
        self.customer_process.store_open = self.store_open

    def get_interarrival_time(self) -> float:
        # return next interarrival time based on peak / off-peak hours
        current_time = self.env.now % (24 * 60)

        if self.config.arrivals.PEAK_START <= current_time < self.config.arrivals.PEAK_END:
            mean = self.config.arrivals.PEAK_MEAN
        else:
            mean = self.config.arrivals.OFF_PEAK_MEAN

        return random.expovariate(1 / mean)

    def run(self):
        # creates customers during store hours
        while True:
            now = self.env.now
            time_of_day = now % (24 * 60)

            # if we outside business hours
            if (
                time_of_day < self.config.time.OPEN_TIME
                or time_of_day >= self.config.time.CLOSE_TIME
            ):
                # calculate when the store will open again
                if time_of_day < self.config.time.OPEN_TIME:
                    next_open = self.config.time.OPEN_TIME
                else:
                    # next day
                    next_open = 24 * 60 + self.config.time.OPEN_TIME

                wait_time = next_open - time_of_day

                # close store (if its not already closed)
                if self.store_open.triggered:
                    self.store_open = self.env.event()
                    self.customer_process.store_open = self.store_open


                yield self.env.timeout(wait_time)
                # open store
                self.store_open.succeed()

                continue

            # within business hours → normal arrival
            interarrival = self.get_interarrival_time()
            yield self.env.timeout(interarrival)

            time_of_day = self.env.now % (24 * 60)
            # skip processing if we are past closing time
            if time_of_day >= self.config.time.CLOSE_TIME:
                continue

            self.customer_id += 1
            self.stats.total_customers += 1

            is_seated = random.random() < self.config.consumption.SEATED_PROB

            customer = Customer(
                id=self.customer_id,
                arrival_time=self.env.now,
                is_seated=is_seated
            )

            self.env.process(self.customer_process.run(customer))
            # print(f"{self.env.now:.2f} | Customer {customer.id} arrived")