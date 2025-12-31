import simpy

class Resources:
    """
    Container class for all SimPy resources of the system.
    No customer logic is implemented here.
    """

    def __init__(self, env: simpy.Environment, config):
        self.env = env
        self.config = config

        # Cashier (order & payment)
        self.cashier = simpy.PriorityResource(
            env,
            capacity=config.resources.CASHIERS
        )

        # Production resources
        self.scooper = simpy.PriorityResource(
            env,
            capacity=config.resources.SCOOPERS
        )

        self.waffle_maker = simpy.Resource(
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

        # Service for seated customers
        self.waiter = simpy.Resource(
            env,
            capacity=config.resources.WAITERS
        )

        self.tables = simpy.Resource(
            env,
            capacity=config.resources.TABLES
        )
