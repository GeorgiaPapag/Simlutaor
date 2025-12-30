import random

# --------------------------------------------------
# Mapping σταδίων -> (resource_name, service_time_key)
# --------------------------------------------------
STAGE_RESOURCES = {
    "coffee": ("barista", "COFFEE"),
    "ice_cream": ("scooper", "ICE_CREAM_PER_SCOOP"),  # per scoop
    "toppings": ("toppings_staff", "TOPPINGS"),
    "waffle": ("waffle_maker", "WAFFLE"),
    "milkshake": ("scooper", "MILKSHAKE"),            # απλοποίηση: ίδιος πόρος με scooper
    # "small_purchase" θα το χειριστούμε ειδικά (χωρίς πόρο)
}

class CustomerProcess:
    def __init__(self, env, resources, config):
        self.env = env
        self.resources = resources
        self.config = config

    # --------------------------------------------------
    # Generic stage execution (queue + abandon + service)
    # --------------------------------------------------
    def process_stage(self, stage: str):
        # small_purchase: δεν έχεις ξεχωριστό resource/time στο config,
        # οπότε (προς το παρόν) θεωρούμε ότι δεν δημιουργεί στάδιο παραγωγής.
        if stage == "small_purchase":
            return True

        if stage not in STAGE_RESOURCES:
            raise KeyError(f"Unknown stage '{stage}'. Add it to STAGE_RESOURCES.")

        resource_name, time_key = STAGE_RESOURCES[stage]
        resource = getattr(self.resources, resource_name)

        with resource.request() as req:
            result = yield req | self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)

            # Abandon if waited too long (σε ΟΠΟΙΑΔΗΠΟΤΕ ουρά παραγωγής)
            if req not in result:
                return False

            # Service time from config (συνήθως (mean, std) ή (min, max))
            time_params = getattr(self.config.service_times, time_key)

            # ειδική περίπτωση: παγωτό = χρόνος ανά μπάλα
            if stage == "ice_cream":
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

    # --------------------------------------------------
    # Main customer flow
    # --------------------------------------------------
    def run(self, customer):
        print(f"{self.env.now:.2f} | Customer {customer.id} started")
        # ---- Order at cashier ----
        with self.resources.cashier.request(priority=0) as req:
            result = yield req | self.env.timeout(self.config.waiting_rules.MAX_QUEUE_WAIT)
            if req not in result:
                return

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

        # ---- Loop of stages ----
        while True:
            print(
                f"{self.env.now:.2f} | "
                f"Customer {customer.id} enters stage {current_stage}"
            )

            ok = yield from self.process_stage(current_stage)
            
            if not ok:
                print(
                    f"{self.env.now:.2f} | "
                    f"Customer {customer.id} abandoned at {current_stage}"
                )
                return  # abandon

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

            current_stage = next_stage

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
