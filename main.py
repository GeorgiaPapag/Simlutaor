import simpy
from SimConfig import SimulationConfig
from Resources import Resources
from ArrivalProcess import ArrivalProcess
from CustomerProcess import CustomerProcess

def main():
    env = simpy.Environment()
    config = SimulationConfig()

    resources = Resources(env, config)
    customer_process = CustomerProcess(env, resources, config)
    arrival_process = ArrivalProcess(env, config, customer_process)

    env.process(arrival_process.run())
    env.run(until=90)

if __name__ == "__main__":
    main()
