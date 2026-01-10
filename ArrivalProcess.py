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
        self.store_open.succeed()  # αρχικά ανοιχτό (θα κλείσει στο πρώτο CLOSE)
        self.customer_process.store_open = self.store_open


    def get_interarrival_time(self) -> float:
        """Return next interarrival time based on peak / off-peak hours."""
        current_time = self.env.now % (24 * 60)

        if self.config.arrivals.PEAK_START <= current_time < self.config.arrivals.PEAK_END:
            mean = self.config.arrivals.PEAK_MEAN
        else:
            mean = self.config.arrivals.OFF_PEAK_MEAN

        return random.expovariate(1 / mean)

    def run(self):
        """SimPy process that generates arriving customers,
        respecting store opening hours."""
        while True:
            now = self.env.now
            time_of_day = now % (24 * 60)

            # ----------------------------------
            # Αν είμαστε εκτός ωραρίου
            # ----------------------------------
            
            if (
                time_of_day < self.config.time.OPEN_TIME
                or time_of_day >= self.config.time.CLOSE_TIME
            ):
                # υπολόγισε πότε ανοίγει ξανά
                if time_of_day < self.config.time.OPEN_TIME:
                    next_open = self.config.time.OPEN_TIME
                else:
                    # επόμενη μέρα
                    next_open = 24 * 60 + self.config.time.OPEN_TIME

                wait_time = next_open - time_of_day

                # ΚΛΕΙΣΙΜΟ ΚΑΤΑΣΤΗΜΑΤΟΣ (μόνο αν δεν είναι ήδη κλειστό)
                if self.store_open.triggered:
                    self.store_open = self.env.event()
                    self.customer_process.store_open = self.store_open


                yield self.env.timeout(wait_time)
                # ΑΝΟΙΓΜΑ ΚΑΤΑΣΤΗΜΑΤΟΣ
                self.store_open.succeed()

                continue

            # ----------------------------------
            # Εντός ωραρίου → κανονική άφιξη
            # ----------------------------------
            interarrival = self.get_interarrival_time()
            yield self.env.timeout(interarrival)

            # Μπορεί να περάσαμε εκτός ωραρίου ενδιάμεσα
            time_of_day = self.env.now % (24 * 60)
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
            print(f"{self.env.now:.2f} | Customer {customer.id} arrived")
