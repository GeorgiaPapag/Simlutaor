import simpy

from SimConfig import SimulationConfig, SimTimeConfig
from Resources import Resources
from Stats import Stats
from ArrivalProcess import ArrivalProcess
from CustomerProcess import CustomerProcess
import random


def main():
    random.seed(42)

    config = SimulationConfig()

    DAYS = config.time.RUN_LENGTH_DAYS
    DAY_LENGTH = 24 * 60                 # ημερολογιακή μέρα
    OPEN_TIME = config.time.OPEN_TIME
    CLOSE_TIME = config.time.CLOSE_TIME
    WARM_UP = config.time.WARM_UP_TIME   # σε λεπτά

    stats = Stats()

    for day in range(DAYS):
        # print(f"\n===== DAY {day + 1} =====")

        env = simpy.Environment()

        resources = Resources(env, config)
        customer_process = CustomerProcess(env, resources, config, stats)
        arrival_process = ArrivalProcess(env, config, customer_process, stats)

        env.process(arrival_process.run())

        # -------------------------
        # 1️⃣ ΜΟΝΟ ΤΗΝ ΠΡΩΤΗ ΜΕΡΑ: warm-up σε λεπτά
        # -------------------------
        if day == 0 and WARM_UP > 0:
            warm_up_end = OPEN_TIME + WARM_UP

            # τρέχουμε μέχρι να τελειώσει το warm-up
            env.run(until=warm_up_end)

            # μηδενίζουμε ΜΟΝΟ stats
            stats.reset()

            # συνεχίζουμε την ίδια μέρα μέχρι τα 24h
            env.run(until=CLOSE_TIME)

        else:
            # -------------------------
            # 2️⃣ Κανονική steady-state μέρα
            # -------------------------
            env.run(until=CLOSE_TIME)

    # -------------------------
    # Τελική αναφορά

    steady_time = (DAYS * DAY_LENGTH) - (OPEN_TIME + WARM_UP)

    print("cashier_waits samples:", stats.cashier_waits[:5])
    print("scooper_waits samples:", stats.scooper_waits[:5])

    print("---- STATS ----")
    print("Total customers:", stats.total_customers)
    print("Abandoned customers:", stats.abandoned_customers)

    print("---- PERFORMANCE METRICS ----")
    print("Total customers:", stats.total_customers)
    print("Abandonment rate:",
        stats.abandoned_customers / stats.total_customers)

    cashier_p95 = stats.p95_cashier_wait()
    print(
        "Cashier constraint (<6'): ",
        cashier_p95, "=","OK" if cashier_p95 < 6 else "VIOLATED"
    )

    scooper_p95 = stats.p95_scooper_wait()
    print(
        "Scooper constraint (<5'): ",
        scooper_p95, "=", "OK" if scooper_p95 < 5 else "VIOLATED"
    )

    # SIM_TIME = steady_time

    # print("---- UTILIZATION ----")
    # for res, busy in stats.resource_busy_time.items():
    #     utilization = busy / SIM_TIME
    #     print(
    #         f"{res}: {utilization:.2%}",
    #         "OK" if 0.70 <= utilization <= 0.85 else "⚠️"
    #     )

    OPEN_MINUTES_PER_DAY = CLOSE_TIME - OPEN_TIME
    steady_time = (OPEN_MINUTES_PER_DAY * DAYS) - WARM_UP

    print("---- UTILIZATION ----")
    for res, busy in stats.resource_busy_time.items():
        utilization = busy / steady_time
        print(
            f"{res}: {utilization:.2%}",
            "OK" if 0.70 <= utilization <= 0.85 else "⚠️"
        )



if __name__ == "__main__":
    main()

