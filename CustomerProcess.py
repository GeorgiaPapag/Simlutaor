import random

# Stage mapping -> (resource_name, service_time_key)
STAGE_RESOURCES = {
    "ice_cream": ("scooper", "ICE_CREAM_PER_SCOOP"),
    "toppings": ("toppings_staff", "TOPPINGS"),
    "waffle": ("waffle_maker", "WAFFLE"),
    "coffee": ("barista", "COFFEE"),
    "milkshake": ("barista", "MILKSHAKE"),
}

class CustomerProcess:
    def __init__(self, env, resources, config, stats):
        self.env = env
        self.resources = resources
        self.config = config
        self.stats = stats

    # generic stage execution (queue + abandon + service)
    def process_stage(self, customer, stage: str):
        # small_purchase
        if stage == "small_purchase":
            return True
        
        # have the scooper assist if possible
        if stage == "toppings":
            return (yield from self.process_toppings_with_help(customer))
        
        # if stage in ("coffee", "milkshake"):
        #     print(f"{self.env.now:.2f} | Barista busy with {stage}")

        if stage not in STAGE_RESOURCES:
            raise KeyError(f"Unknown stage '{stage}'. Add it to STAGE_RESOURCES.")

        resource_name, time_key = STAGE_RESOURCES[stage]
        resource = getattr(self.resources, resource_name)

        # priority definition
        priority = 1  # default

        # scooper priority: ice cream only after waffle
        if stage == "ice_cream" and customer.previous_stage == "waffle":
            priority = 0

        # barista priority: coffee only after ice cream
        if stage == "coffee" and customer.previous_stage == "ice_cream":
            priority = 0
        
        # print(
        #     f"{self.env.now:.2f} | DEBUG priority: "
        #     f"cust={customer.id}, stage={stage}, prev={customer.previous_stage}, priority={priority}"
        # )

        start_wait_scooping = None

        # only for ice_cream
        if stage == "ice_cream":
            start_wait_scooping = self.env.now # start of waiting

        with resource.request(priority=priority) as req:
            result = yield req | self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)

            # abandon if waited too long
            if req not in result:
                if stage == "ice_cream":
                    self.stats.scooper_waits.append(
                        self.config.waiting_rules.MAX_QUEUE_WAIT
                    )
                self.stats.abandoned_customers += 1
                return False

            # end of waiting
            if stage == "ice_cream":
                self.stats.scooper_waits.append(self.env.now - start_wait_scooping)

            # service time from config
            time_params = getattr(self.config.service_times, time_key)

            # special case: ice cream = time per scoop
            if stage == "ice_cream":
                # service time calculation
                scoops_probs = self.config.ice_cream.SCOOPS_PROBS  # {1:0.40,2:0.45,3:0.15}
                scoops = random.choices(
                    population=list(scoops_probs.keys()),
                    weights=list(scoops_probs.values())
                    )[0]

                # time_params
                per_scoop = self.sample_time(
                    self.config.service_times.ICE_CREAM_PER_SCOOP
                )
                service_time = scoops * per_scoop
            else:
                service_time = self.sample_time(time_params)

            yield self.env.timeout(service_time)

            # resource utilization
            if resource_name in self.stats.resource_busy_time:
                self.stats.resource_busy_time[resource_name] += service_time

        return True
    
    def sample_time(self, spec):
        # spec: DistSpec form SimConfig
        if spec.dist == "uniform":
            return random.uniform(spec.a, spec.b)
        elif spec.dist == "normal":
            return max(0.0, random.gauss(spec.a, spec.b)) # discard negative values
        else:
            raise ValueError(f"Unknown distribution {spec.dist}")


    # initial product choice (uses INITIAL_ORDER_PROBS)
    def choose_initial_product(self) -> str:
        probs = self.config.order_choices.INITIAL_ORDER_PROBS
        return random.choices(
            population=list(probs.keys()),
            weights=list(probs.values())
        )[0]

    def choose_next_stage(self, stage: str, came_from_waffle: bool) -> str:
        # if a waffle just finished → 100% goes to ice cream
        if stage == "waffle":
            return "ice_cream"

        # if the current stage is ice cream and the previous stage was waffle
        if stage == "ice_cream" and came_from_waffle:
            probs = self.config.continuations.CONTINUATION_PROBS["ice_cream_after_waffle"]
        else:
            probs = self.config.continuations.CONTINUATION_PROBS[stage]

        return random.choices(
            population=list(probs.keys()),
            weights=list(probs.values())
        )[0]

    def process_toppings_with_help(self, customer):
        # Toppings:
            # - primary: toppings_staff
            # - helper: scooper (only if immediately free)

        start_wait = self.env.now

        # check if the scooper is immediately available
        if self.resources.scooper.count < self.resources.scooper.capacity:
            # Scooper helps immediately (no waiting)
            with self.resources.scooper.request(priority=1) as req:
                yield req

                wait_time = self.env.now - start_wait
                self.stats.toppings_waits.append(wait_time)

                service_time = self.sample_time(self.config.service_times.TOPPINGS)
                yield self.env.timeout(service_time)

                self.stats.resource_busy_time["scooper"] += service_time

                # print(f"{self.env.now:.2f} | Toppings served by scooper")
                return True

        # follow the normal toppings_staff queue
        with self.resources.toppings_staff.request() as req:
            result = yield req | self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)

            if req not in result:
                self.stats.abandoned_customers += 1
                self.stats.toppings_waits.append(
                    self.config.waiting_rules.MAX_QUEUE_WAIT
                )
                return False

            wait_time = self.env.now - start_wait
            self.stats.toppings_waits.append(wait_time)

            service_time = self.sample_time(self.config.service_times.TOPPINGS)
            yield self.env.timeout(service_time)

            self.stats.resource_busy_time["toppings_staff"] += service_time

            # print(f"{self.env.now:.2f} | Toppings served by toppings_staff")
        return True
    

    # cleaning process
    def clean_table_process(self, clean_time: float, customer_id: int):
        # print(f"[{self.env.now:.2f}] Customer {customer_id}: TABLE CLEANING STARTED")
        with self.resources.waiter.request() as w_req:
            yield w_req
            yield self.env.timeout(clean_time)
            self.stats.resource_busy_time["waiter"] += clean_time
        # print(f"[{self.env.now:.2f}] Customer {customer_id}: TABLE CLEANED → AVAILABLE")

   # main customer flow
    def run(self, customer):
        # print(f"{self.env.now:.2f} | Customer {customer.id} started")
        
        # start time
        start_wait_cashier = self.env.now
        pending_table_clean = None

        current_stage = self.choose_initial_product()

        # "express" scenario: small_purchase goes to express cashier and finishes
        if getattr(self.config, "scenario", "base") == "express" and current_stage == "small_purchase":
            start_wait = self.env.now

            with self.resources.cashier_express.request(priority=0) as req:
                result = yield req | self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)

                if req not in result:
                    self.stats.abandoned_customers += 1
                    return

                # measure waiting time like at the cashier λίστα)
                self.stats.cashier_waits.append(self.env.now - start_wait)

                # service: order + payment
                order_t = self.sample_time(self.config.service_times.ORDER)
                pay_t = self.sample_time(self.config.service_times.PAYMENT)
                service_t = order_t + pay_t

                yield self.env.timeout(service_t)
                self.stats.resource_busy_time["cashier_express"] += service_t

            return

        # normal order at cashier for all
        with self.resources.cashier.request(priority=0) as req:
            result = yield req | self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)
            if req not in result:
                self.stats.abandoned_customers += 1
                return
            
            # calculate time
            self.stats.add_cashier_wait(self.env.now - start_wait_cashier)

            service_time = self.sample_time(self.config.service_times.ORDER)
            # utilization
            yield self.env.timeout(service_time)
            self.stats.resource_busy_time["cashier"] += service_time
            
        # print(f"{self.env.now:.2f} | Customer {customer.id} ordered")

        # flag: if the incoming ice cream is after waffle
        next_icecream_is_after_waffle = False

        previous_stage = None
        customer.previous_stage = previous_stage

        # loop of stages
        while True:
            # print(
            #     f"{self.env.now:.2f} | "
            #     f"Customer {customer.id} enters stage {current_stage}"
            # )

            ok = yield from self.process_stage(customer, current_stage)

            if not ok:
                # print(f"{self.env.now:.2f} | f"Customer {customer.id} abandoned at {current_stage}")
                return  # abandon

            # customer.is_continuation = True

            # boolean: if a waffle was just made, the next ice cream is after waffle
            came_from_waffle = next_icecream_is_after_waffle
            next_stage = self.choose_next_stage(current_stage, came_from_waffle)

            if next_stage == "pay":
                # print(f"{self.env.now:.2f} | f"Customer {customer.id} finished (go to pay)")
                break
            
            # update flag for the next round
            if current_stage == "waffle":
                next_icecream_is_after_waffle = True
            else:
                # once used (or no longer valid), reset it to zero
                next_icecream_is_after_waffle = False

            previous_stage = current_stage
            current_stage = next_stage
            customer.previous_stage = previous_stage

        # seated or takeaway
        if customer.is_seated:
            # print(f"{self.env.now:.2f} | Customer {customer.id} wants table")
            
            # record that a table was requested
            self.stats.table_seekers += 1
            start_wait_table = self.env.now

             # waiting for a table (up to 5 minutes)
            with self.resources.tables.request() as table_req:
                result = yield table_req | self.env.timeout(
                    self.config.waiting_rules.MAX_TABLE_WAIT
                )

                if table_req not in result:
                    # didnt get a table → switches to takeaway
                    self.stats.table_waits.append(self.config.waiting_rules.MAX_TABLE_WAIT)
                    self.stats.table_timeouts_to_takeaway += 1
                    customer.is_seated = False
                    # print(f"[{self.env.now:.2f}] Customer {customer.id}: TABLE OCCUPIED")
                else:
                    self.stats.table_waits.append(self.env.now - start_wait_table)

                    # served by waiter
                    with self.resources.waiter.request() as w_req:
                        yield w_req
                        serve_time = self.sample_time(self.config.service_times.SERVING)
                        yield self.env.timeout(serve_time)
                        
                        # utilization
                        self.stats.resource_busy_time["waiter"] += serve_time

                        # print(f"{self.env.now:.2f} | Customer {customer.id} served")

                    # Consumption (no resource required)
                    cons_time = self.sample_time(self.config.service_times.CONSUMPTION)
                    yield self.env.timeout(cons_time)

                    # print(f"[{self.env.now:.2f}] Customer {customer.id}: FINISHED CONSUMPTION (leaves table)")

                    clean_time = self.sample_time(self.config.service_times.TABLE_CLEANING)
                    pending_table_clean = self.env.process(self.clean_table_process(clean_time, customer.id))

                    # print(f"{self.env.now:.2f} | Customer {customer.id} finished consumption")

        # Payment (no abandonment)
        # print(f"[{self.env.now:.2f}] Customer {customer.id}: GO PAY (seated={customer.is_seated})")

        with self.resources.cashier.request(priority=1) as req:

            if pending_table_clean is not None:
                # wait for whichever comes first: cashier or cleaning to finish
                result = yield req | pending_table_clean
                # if cleaning finishes first, continue waiting for the cashier
                if req not in result:
                    yield req
            else:
                yield req

            pay_time = self.sample_time(self.config.service_times.PAYMENT)

            yield self.env.timeout(pay_time)

            self.stats.resource_busy_time["cashier"] += pay_time

        # print(f"{self.env.now:.2f} | Customer {customer.id} exited system")
        return
