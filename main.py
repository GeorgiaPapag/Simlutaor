import simpy

from SimConfig import SimulationConfig
from ArrivalProcess import ArrivalProcess
from CustomerProcess import CustomerProcess


def main():
    env = simpy.Environment()
    config = SimulationConfig()

    customer_process = CustomerProcess(env)
    arrival_process = ArrivalProcess(env, config, customer_process)

    env.process(arrival_process.run())
    env.run(until=10)   # 2 ώρες simulation για test


if __name__ == "__main__":
    main()
