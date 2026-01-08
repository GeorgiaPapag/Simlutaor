import simpy
from SimConfig import SimulationConfig, SimTimeConfig
from Resources import Resources
from ArrivalProcess import ArrivalProcess
from CustomerProcess import CustomerProcess
from Stats import Stats
import numpy as np

def main():
    env = simpy.Environment()
    config = SimulationConfig()
    stats = Stats()

    resources = Resources(env, config)
    customer_process = CustomerProcess(env, resources, config, stats)
    arrival_process = ArrivalProcess(env, config, customer_process, stats)

    # Χρονικές παράμετροι από config
    WARM_UP = config.time.WARM_UP_TIME
    DAYS = config.time.RUN_LENGTH_DAYS
    DAY_LENGTH = config.time.DAY_LENGTH

    TOTAL_TIME = config.time.RUN_LENGTH_DAYS * 24 * 60
    STEADY_TIME = TOTAL_TIME - config.time.WARM_UP_TIME


    # Ξεκινάει η διαδικασία αφίξεων
    env.process(arrival_process.run())

    last_time = 0.0

    # 1️⃣ Warm-up period
    env.run(until=WARM_UP)

    # Reset στατιστικών (όχι πόρων / ουρών)
    stats.reset()

    # 2️⃣ Κύρια προσομοίωση (steady state)
    env.run(until=TOTAL_TIME)
    
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
        "Cashier constraint (<5'): ",
        scooper_p95, "=", "OK" if scooper_p95 < 5 else "VIOLATED"
    )

    SIM_TIME = STEADY_TIME

    print("---- UTILIZATION ----")
    for res, busy in stats.resource_busy_time.items():
        utilization = busy / SIM_TIME
        print(
            f"{res}: {utilization:.2%}",
            "OK" if 0.70 <= utilization <= 0.85 else "⚠️"
        )

    
if __name__ == "__main__":
    main()


