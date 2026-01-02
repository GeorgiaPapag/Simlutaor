import random

# --------------------------------------------------
# Mapping σταδίων -> (resource_name, service_time_key)
# --------------------------------------------------
STAGE_RESOURCES = {
    "ice_cream": ("scooper", "ICE_CREAM_PER_SCOOP"),
    "toppings": ("toppings_staff", "TOPPINGS"),  # με βοήθεια scooper
    "waffle": ("waffle_maker", "WAFFLE"),
    "coffee": ("barista", "COFFEE"),
    "milkshake": ("barista", "MILKSHAKE"),  # 👈 ΜΟΝΟ barista
}

class CustomerProcess:
    def __init__(self, env, resources, config, stats):
        self.env = env
        self.resources = resources
        self.config = config
        self.stats = stats

    # Generic stage execution (queue + abandon + service)
    # --------------------------------------------------
    def process_stage(self, customer, stage: str):
        # small_purchase: δεν έχεις ξεχωριστό resource/time στο config,
        if stage == "small_purchase":
            return True
        
        # βάζω τον scooper να βοηθήσει αν μπορεί
        if stage == "toppings":
         return (yield from self.process_toppings_with_help(customer))
        
        if stage in ("coffee", "milkshake"):
            print(f"{self.env.now:.2f} | Barista busy with {stage}")

        if stage not in STAGE_RESOURCES:
            raise KeyError(f"Unknown stage '{stage}'. Add it to STAGE_RESOURCES.")

        resource_name, time_key = STAGE_RESOURCES[stage]
        resource = getattr(self.resources, resource_name)

        # ΟΡΙΣΜΟΣ ΠΡΟΤΕΡΑΙΟΤΗΤΑΣ 
        priority = 1  # default

        # Scooper priority: παγωτό ΜΟΝΟ μετά από βάφλα
        if stage == "ice_cream" and customer.previous_stage == "waffle":
            priority = 0

        #  Barista priority: καφές ΜΟΝΟ μετά από παγωτό
        if stage == "coffee" and customer.previous_stage == "ice_cream":
            priority = 0
        
        print(
            f"{self.env.now:.2f} | DEBUG priority: "
            f"cust={customer.id}, stage={stage}, prev={customer.previous_stage}, priority={priority}"
        )

        start_wait_scooping = None

        # only for ice_cream
        if stage == "ice_cream":
            start_wait_scooping = self.env.now # start of waiting

        with resource.request(priority=priority) as req:
            result = yield req | self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)

            # Abandon if waited too long (σε ΟΠΟΙΑΔΗΠΟΤΕ ουρά παραγωγής)
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

            # Service time from config (συνήθως (mean, std) ή (min, max))
            time_params = getattr(self.config.service_times, time_key)

            # ειδική περίπτωση: παγωτό = χρόνος ανά μπάλα
            if stage == "ice_cream":
                # ---- service time calculation
                scoops_probs = self.config.ice_cream.SCOOPS_PROBS  # {1:0.40,2:0.45,3:0.15}
                scoops = random.choices(
                    population=list(scoops_probs.keys()),
                    weights=list(scoops_probs.values())
                    )[0]

                # time_params = (mean, std) per scoop
                mean, std = time_params
                per_scoop = max(0.0, random.gauss(mean, std))
                service_time = scoops * per_scoop
            else:
                # γενικός χειρισμός tuple
                if isinstance(time_params, tuple) and len(time_params) == 2:
                    a, b = time_params
                    # Δεν ξέρουμε εδώ αν είναι (min,max) ή (mean,std) — εσύ το κρατάς ως tuple.
                    # Ακολουθούμε την προσέγγιση που είχες: gauss για (mean,std).
                    # Αν θες uniform για (min,max), το αλλάζουμε μετά με σαφή κανόνα ανά stage.
                    service_time = max(0.0, random.gauss(a, b))
                else:
                    service_time = max(0.0, float(time_params))

            yield self.env.timeout(service_time)

        return True
    
    def sample_time(self, param):
        """
        param is either (min,max) for uniform or (mean,std) for normal
        """
        a, b = param
        # SERVING είναι uniform στο config, ORDER επίσης uniform
        # PAYMENT/CONSUMPTION είναι normal στο config (mean,std)
        # Εμείς δεν ξεχωρίζουμε με tag, απλά εφαρμόζουμε:
        # - αν θες 100% σωστό: θα το κάνουμε μετά με flags.
        # Προς το παρόν: χρησιμοποιούμε normal για ό,τι έχει std "λογικό" και uniform για serving/order.
        return max(0.0, random.gauss(a, b))


    # --------------------------------------------------
    # Initial product choice (uses INITIAL_ORDER_PROBS)
    # --------------------------------------------------
    def choose_initial_product(self) -> str:
        probs = self.config.order_choices.INITIAL_ORDER_PROBS
        return random.choices(
            population=list(probs.keys()),
            weights=list(probs.values())
        )[0]

    # --------------------------------------------------
    # Continuation decision (handles waffle special rule)
    # --------------------------------------------------
    def choose_next_stage(self, stage: str, came_from_waffle: bool) -> str:
        # Αν ΜΟΛΙΣ τελείωσε βάφλα -> 100% πάει σε παγωτό
        if stage == "waffle":
            return "ice_cream"

        # Αν το τρέχον στάδιο είναι παγωτό και ΠΡΟΗΓΟΥΜΕΝΟ ήταν βάφλα,
        # τότε αλλάζει το routing: 45% toppings, 55% pay
        if stage == "ice_cream" and came_from_waffle:
            probs = self.config.continuations.CONTINUATION_PROBS["ice_cream_after_waffle"]
        else:
            probs = self.config.continuations.CONTINUATION_PROBS[stage]

        return random.choices(
            population=list(probs.keys()),
            weights=list(probs.values())
        )[0]
    
    def process_toppings_with_help(self, customer):
        """
        Toppings can be processed either by:
        - toppings_staff (primary)
        - scooper (helper)
        """

        print(
            f"{self.env.now:.2f} | "
            f"DEBUG toppings entry: "
            f"toppings_staff busy={self.resources.toppings_staff.count} queue={len(self.resources.toppings_staff.queue)} | "
            f"scooper busy={self.resources.scooper.count} queue={len(self.resources.scooper.queue)}"
        )

        toppings_req = self.resources.toppings_staff.request()
        scooper_req = self.resources.scooper.request()

        result = yield (
            toppings_req |
            scooper_req |
            self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)
        )

        # Abandonment
        if result == {}:
            self.stats.abandoned_customers += 1 # abandon stat
            return False

        if toppings_req in result:
            server = "toppings_staff"
            yield toppings_req
            scooper_req.cancel()

        elif scooper_req in result:
            server = "scooper"
            yield scooper_req
            toppings_req.cancel()

        else:
            return False

        # Service time
        service_time = self.config.service_times.TOPPINGS
        if isinstance(service_time, tuple):
            service_time = random.uniform(*service_time)

        yield self.env.timeout(service_time)

        print(f"{self.env.now:.2f} | Toppings served by {server}")

        return True

    # Main customer flow
    # --------------------------------------------------
    def run(self, customer):
        print(f"{self.env.now:.2f} | Customer {customer.id} started")
        
        # start time
        start_wait_cashier = self.env.now

        # ---- Order at cashier ----
        with self.resources.cashier.request(priority=0) as req:
            result = yield req | self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)
            if req not in result:
                self.stats.abandoned_customers += 1
                return
            
            # calculate time
            self.stats.add_cashier_wait(self.env.now - start_wait_cashier)

            order_min, order_max = self.config.service_times.ORDER
            yield self.env.timeout(random.uniform(order_min, order_max))
            
        print(f"{self.env.now:.2f} | Customer {customer.id} ordered")

        # ---- Initial product ----
        current_stage = self.choose_initial_product()
        print(
            f"{self.env.now:.2f} | "
            f"Customer {customer.id} initial product = {current_stage}"
        )

        # flag: αν το παγωτό που έρχεται είναι "μετά από βάφλα"
        next_icecream_is_after_waffle = False


        # customer.is_continuation = False
        previous_stage = None
        customer.previous_stage = previous_stage

        # ---- Loop of stages ----
        while True:
            print(
                f"{self.env.now:.2f} | "
                f"Customer {customer.id} enters stage {current_stage}"
            )

            ok = yield from self.process_stage(customer, current_stage)

            if not ok:
                print(
                    f"{self.env.now:.2f} | "
                    f"Customer {customer.id} abandoned at {current_stage}"
                )
                return  # abandon

            # customer.is_continuation = True


            # Αν μόλις έκανες βάφλα, το επόμενο παγωτό είναι "after waffle"
            came_from_waffle = next_icecream_is_after_waffle
            next_stage = self.choose_next_stage(current_stage, came_from_waffle)

            if next_stage == "pay":
                print(
                    f"{self.env.now:.2f} | "
                    f"Customer {customer.id} finished (go to pay)"
                )
                break
            
            # ενημέρωση flag για τον επόμενο γύρο
            if current_stage == "waffle":
                next_icecream_is_after_waffle = True
            else:
                # μόλις χρησιμοποιήθηκε (ή δεν ισχύει), το μηδενίζουμε
                next_icecream_is_after_waffle = False

            if next_stage == "pay":
                break

            previous_stage = current_stage
            current_stage = next_stage
            customer.previous_stage = previous_stage

        # -------------------------
        # Seated vs Takeaway
        # -------------------------
        if customer.is_seated:
            print(f"{self.env.now:.2f} | Customer {customer.id} wants table")
             # 1️⃣ Αναμονή για τραπέζι (μέχρι 5')
            with self.resources.tables.request() as table_req:
                result = yield table_req | self.env.timeout(
                    self.config.waiting_rules.MAX_TABLE_WAIT
                )

                if table_req not in result:
                    # δεν βρήκε τραπέζι → γίνεται πακέτο
                    customer.is_seated = False
                else:
                    # Σερβίρισμα από σερβιτόρο
                    with self.resources.waiter.request() as w_req:
                        yield w_req
                        serve_min, serve_max = self.config.service_times.SERVING
                        yield self.env.timeout(random.uniform(serve_min, serve_max))
                        print(f"{self.env.now:.2f} | Customer {customer.id} served")

                    # Κατανάλωση (χωρίς πόρο)
                    cons_mean, cons_std = self.config.service_times.CONSUMPTION
                    yield self.env.timeout(max(0, random.gauss(cons_mean, cons_std)))
                    print(f"{self.env.now:.2f} | Customer {customer.id} finished consumption")

                    # Τακτοποίηση τραπεζιού από σερβιτόρο
                    with self.resources.waiter.request() as w_req:
                        yield w_req
                        clean_min, clean_max = self.config.service_times.TABLE_CLEANING
                        yield self.env.timeout(random.uniform(clean_min, clean_max))
                    # (table released automatically when leaving "with tables.request()")
                    print(f"{self.env.now:.2f} | Customer {customer.id} table cleaned")


        # -------------------------
        # Payment (no abandonment)
        # -------------------------
        with self.resources.cashier.request(priority=1) as req:
            print(f"{self.env.now:.2f} | Customer {customer.id} paying")
            yield req

            pay_min, pay_max = self.config.service_times.PAYMENT
            yield self.env.timeout(random.uniform(pay_min, pay_max))

        print(f"{self.env.now:.2f} | Customer {customer.id} exited system")
        return
