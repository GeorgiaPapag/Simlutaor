import simpy

class Resources:
    # resources of the system

    def __init__(self, env: simpy.Environment, config):
        self.env = env
        self.config = config

        # cashier (order & payment)
        self.cashier = simpy.PriorityResource(
            env,
            capacity=config.resources.CASHIERS
        )

        self.cashier_express = simpy.PriorityResource(env, capacity=1)

        # production resources
        self.scooper = simpy.PriorityResource(
            env,
            capacity=config.resources.SCOOPERS
        )

        self.waffle_maker = simpy.PriorityResource(
            env,
            capacity=config.resources.WAFFLE_MAKERS
        )

        self.barista = simpy.PriorityResource(
            env,
            capacity=config.resources.BARISTAS
        )

        self.toppings_staff = simpy.Resource(
            env,
            capacity=config.resources.TOPPINGS_STAFF
        )

        # service for seated customers
        self.waiter = simpy.Resource(
            env,
            capacity=config.resources.WAITERS
        )

        self.tables = simpy.Resource(
            env,
            capacity=config.resources.TABLES
        )
