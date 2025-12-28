# pip install simpy numpy
import simpy as sp
import numpy as np

# -----------------------------
# Βοηθητικές κατανομές
# -----------------------------
def tri(rng, left, mode, right):
    # numpy: triangular(left, mode, right)
    assert left <= mode <= right, "Triangular params must satisfy left <= mode <= right"
    return float(rng.triangular(left, mode, right))


def normal_pos(rng, mean, sd):
    x = rng.normal(mean, sd)
    while x <= 0:
        x = rng.normal(mean, sd)
    return float(x)

# -----------------------------
# Metrics
# -----------------------------
class Metrics:
    def __init__(self):
        self.waits = []
        self.served = 0
        self.reneged = 0
        self.busy_time = 0.0
        self.last_change = 0.0
        self.busy = 0  # number of busy servers (0/1 here)

    def on_service_start(self, t):
        # capture utilization (time-weighted)
        self.busy_time += self.busy * (t - self.last_change)
        self.last_change = t
        self.busy += 1

    def on_service_end(self, t):
        self.busy_time += self.busy * (t - self.last_change)
        self.last_change = t
        self.busy -= 1

    def finalize(self, t_end):
        self.busy_time += self.busy * (t_end - self.last_change)

# -----------------------------
# Shop (περιβάλλον)
# -----------------------------
class Shop:
    def __init__(self, env, seed=0):
        self.env = env
        self.server = sp.Resource(env, capacity=1)
        self.rng = np.random.default_rng(seed)
        self.m = Metrics()

    def service_time(self, product):
        if product == "ice":
            return tri(self.rng, 0.3, 0.8, 1.4)
        else:
            return normal_pos(self.rng, 1.2, 0.3)

# -----------------------------
# Διαδικασία πελάτη
# -----------------------------
def customer(env, shop: Shop, patience=4.0):
    t_arr = env.now

    # επιλογή προϊόντος
    product = "ice" if shop.rng.random() < 0.60 else "coffee"

    # αίτημα πόρου με υπομονή
    req = shop.server.request()
    result = yield req | env.timeout(patience)

    if req not in result:  # έληξε η υπομονή
        shop.m.reneged += 1
        # ακύρωση του request
        try:
            shop.server.release(req)
        except:
            pass
        return

    # εξυπηρέτηση
    wait = env.now - t_arr
    shop.m.waits.append(wait)
    shop.m.on_service_start(env.now)

    st = shop.service_time(product)
    yield env.timeout(st)

    shop.m.on_service_end(env.now)
    shop.server.release(req)
    shop.m.served += 1

# -----------------------------
# Διαδικασία αφίξεων
# -----------------------------
def arrivals(env, shop: Shop, mean_iat=5.0, horizon=480.0):
    # δημιουργεί αφίξεις μέχρι horizon (λεπτά)
    while env.now < horizon:
        iat = shop.rng.exponential(mean_iat)
        yield env.timeout(iat)
        env.process(customer(env, shop))

# -----------------------------
# Μία επανάληψη (με warm-up)
# -----------------------------
def run_rep(seed=0, mean_iat=5.0, horizon=480.0, warmup=30.0):
    env = sp.Environment()
    shop = Shop(env, seed)

    env.process(arrivals(env, shop, mean_iat=mean_iat, horizon=horizon + warmup))
    env.run(until=warmup + horizon)

    
    env2 = sp.Environment()
    shop2 = Shop(env2, seed+1)
    env2.process(arrivals(env2, shop2, mean_iat=mean_iat, horizon=horizon))
    env2.run(until=horizon)
    shop2.m.finalize(horizon)

    waits = np.array(shop2.m.waits) if shop2.m.waits else np.array([])
    served = shop2.m.served
    reneged = shop2.m.reneged
    util = shop2.m.busy_time / horizon if horizon > 0 else 0.0
    p95_wait = float(np.percentile(waits, 95)) if waits.size else float('nan')
    avg_wait = float(waits.mean()) if waits.size else float('nan')
    return {
        "served": served,
        "reneged": reneged,
        "p_wait_95": p95_wait,
        "avg_wait": avg_wait,
        "utilization": util
    }

# -----------------------------
# Εκτέλεση demo
# -----------------------------
if __name__ == "__main__":
    REPS = 10
    results = [run_rep(seed=100 + r) for r in range(REPS)]

    def mean(vals): 
        a = np.array(vals, dtype=float)
        return float(np.nanmean(a))

    print("=== Mini Gelato Stand (SimPy) ===")
    print(f"Replications: {REPS}, Horizon: 8 ώρες, Warm-up: 30′")
    print(f"Μ. Εξυπηρετημένοι/rep: {mean([x['served'] for x in results]):.1f}")
    print(f"Μ. Αποχωρήσαντες (reneged)/rep: {mean([x['reneged'] for x in results]):.1f}")
    print(f"Μ. 95ο εκατοστημόριο αναμονής: {mean([x['p_wait_95'] for x in results]):.2f}′")
    print(f"Μ. μέση αναμονή: {mean([x['avg_wait'] for x in results]):.2f}′")
    print(f"Μ. αξιοποίηση server: {mean([x['utilization'] for x in results])*100:.1f}%")
