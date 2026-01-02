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

    cashier_p95 = np.percentile(stats.cashier_waits, 95)
    print("95th percentile cashier wait:", cashier_p95)

    print("95th percentile scooper wait:",
        stats.p95_scooper_wait())

if __name__ == "__main__":
    main()


