class CustomerProcess:
    def __init__(self, env):
        self.env = env

    def run(self, customer):
        """
        Stub process.
        Will be fully implemented in later stages.
        """
        yield self.env.timeout(0)

    # test
    # def run(self, customer):
    #     print(
    #         f"{self.env.now:.2f} | "
    #         f"Customer {customer.id} process started"
    #     )
    #     yield self.env.timeout(0)

