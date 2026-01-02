import simpy
from SimConfig import SimulationConfig
from Resources import Resources
from ArrivalProcess import ArrivalProcess
from CustomerProcess import CustomerProcess
from Stats import Stats

def main():
    env = simpy.Environment()
    config = SimulationConfig()
    stats = Stats()

    resources = Resources(env, config)
    customer_process = CustomerProcess(env, resources, config, stats)
    arrival_process = ArrivalProcess(env, config, customer_process, stats)
    
    env.process(arrival_process.run())
    env.run(until=90)

    print("---- STATS ----")
    print("Total customers:", stats.total_customers)
    print("Abandoned customers:", stats.abandoned_customers)

    if stats.total_customers > 0:
        print(
            "Abandonment rate:",
            stats.abandoned_customers / stats.total_customers
        )

if __name__ == "__main__":
    main()


