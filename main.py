import simpy
from SimConfig import SimulationConfig
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
    

    env.process(arrival_process.run())
    env.run(until=90)
    
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

    SIM_TIME = env.now  # συνολικός χρόνος προσομοίωσης

    print("---- UTILIZATION ----")
    for res, busy in stats.resource_busy_time.items():
        utilization = busy / SIM_TIME
        print(
            f"{res}: {utilization:.2%}",
            "OK" if 0.70 <= utilization <= 0.85 else "⚠️"
        )

    

if __name__ == "__main__":
    main()


