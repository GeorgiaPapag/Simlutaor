# import simpy

# from SimConfig import SimulationConfig, SimTimeConfig
# from Resources import Resources
# from Stats import Stats
# from ArrivalProcess import ArrivalProcess
# from CustomerProcess import CustomerProcess
# import random


# def main():
#     random.seed(42)

#     config = SimulationConfig()

#     DAYS = config.time.RUN_LENGTH_DAYS
#     DAY_LENGTH = 24 * 60                 # ημερολογιακή μέρα
#     OPEN_TIME = config.time.OPEN_TIME
#     CLOSE_TIME = config.time.CLOSE_TIME
#     WARM_UP = config.time.WARM_UP_TIME   # σε λεπτά

#     stats = Stats()

#     for day in range(DAYS):
#         # print(f"\n===== DAY {day + 1} =====")

#         env = simpy.Environment()

#         resources = Resources(env, config)
#         customer_process = CustomerProcess(env, resources, config, stats)
#         arrival_process = ArrivalProcess(env, config, customer_process, stats)

#         env.process(arrival_process.run())

#         # -------------------------
#         # 1️⃣ ΜΟΝΟ ΤΗΝ ΠΡΩΤΗ ΜΕΡΑ: warm-up σε λεπτά
#         # -------------------------
#         if day == 0 and WARM_UP > 0:
#             warm_up_end = OPEN_TIME + WARM_UP

#             # τρέχουμε μέχρι να τελειώσει το warm-up
#             env.run(until=warm_up_end)

#             # μηδενίζουμε ΜΟΝΟ stats
#             stats.reset()

#             # συνεχίζουμε την ίδια μέρα μέχρι τα 24h
#             env.run(until=CLOSE_TIME)

#         else:
#             # -------------------------
#             # 2️⃣ Κανονική steady-state μέρα
#             # -------------------------
#             env.run(until=CLOSE_TIME)

#     # -------------------------
#     # Τελική αναφορά

#     steady_time = (DAYS * DAY_LENGTH) - (OPEN_TIME + WARM_UP)

#     print("cashier_waits samples:", stats.cashier_waits[:5])
#     print("scooper_waits samples:", stats.scooper_waits[:5])

#     print("---- STATS ----")
#     print("Total customers:", stats.total_customers)
#     print("Abandoned customers:", stats.abandoned_customers)

#     print("---- PERFORMANCE METRICS ----")
#     print("Total customers:", stats.total_customers)
#     print("Abandonment rate:",
#         stats.abandoned_customers / stats.total_customers)

#     cashier_p95 = stats.p95_cashier_wait()
#     print(
#         "Cashier constraint (<6'): ",
#         cashier_p95, "=","OK" if cashier_p95 < 6 else "VIOLATED"
#     )

#     scooper_p95 = stats.p95_scooper_wait()
#     print(
#         "Scooper constraint (<5'): ",
#         scooper_p95, "=", "OK" if scooper_p95 < 5 else "VIOLATED"
#     )

#     # SIM_TIME = steady_time

#     # print("---- UTILIZATION ----")
#     # for res, busy in stats.resource_busy_time.items():
#     #     utilization = busy / SIM_TIME
#     #     print(
#     #         f"{res}: {utilization:.2%}",
#     #         "OK" if 0.70 <= utilization <= 0.85 else "⚠️"
#     #     )

#     OPEN_MINUTES_PER_DAY = CLOSE_TIME - OPEN_TIME
#     steady_time = (OPEN_MINUTES_PER_DAY * DAYS) - WARM_UP

#     print("---- UTILIZATION ----")
#     for res, busy in stats.resource_busy_time.items():
#         utilization = busy / steady_time
#         print(
#             f"{res}: {utilization:.2%}",
#             "OK" if 0.70 <= utilization <= 0.85 else "⚠️"
#         )



# if __name__ == "__main__":
#     main()

import simpy
import random
import math
import numpy as np

from SimConfig import SimulationConfig
from Resources import Resources
from Stats import Stats
from ArrivalProcess import ArrivalProcess
from CustomerProcess import CustomerProcess


# --------------------------
# 95% CI helper (t-interval)
# --------------------------
def mean_ci_95(data):
    """
    Returns (mean, low, high) for a 95% confidence interval using t critical value.
    Uses SciPy if available; otherwise uses a solid approximation.
    """
    data = np.array(data, dtype=float)
    n = len(data)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    if n == 1:
        m = float(data[0])
        return m, m, m

    mean = float(data.mean())
    s = float(data.std(ddof=1))

    # Try SciPy for exact t critical
    try:
        from scipy.stats import t as tdist  # type: ignore
        tcrit = float(tdist.ppf(0.975, df=n - 1))
    except Exception:
        # Good approximation for typical coursework replication counts
        # (n >= 15 => tcrit ~ 2.0, slightly higher for n~20)
        if n <= 10:
            tcrit = 2.262  # approx df=9
        elif n <= 20:
            tcrit = 2.093  # approx df=19
        elif n <= 30:
            tcrit = 2.045  # approx df=29
        else:
            tcrit = 1.96   # close to normal for large n

    half = tcrit * s / math.sqrt(n)
    return mean, mean - half, mean + half


# --------------------------
# One replication (ONE full run)
# --------------------------
def run_one_replication(seed: int):
    random.seed(seed)

    config = SimulationConfig()

    DAYS = config.time.RUN_LENGTH_DAYS
    OPEN_TIME = config.time.OPEN_TIME
    CLOSE_TIME = config.time.CLOSE_TIME
    WARM_UP = config.time.WARM_UP_TIME  # minutes

    # IMPORTANT: fresh stats per replication (independent replications)
    stats = Stats()

    # Run DAYS (your existing "per-day env" approach)
    for day in range(DAYS):
        env = simpy.Environment()

        resources = Resources(env, config)
        customer_process = CustomerProcess(env, resources, config, stats)
        arrival_process = ArrivalProcess(env, config, customer_process, stats)

        env.process(arrival_process.run())

        if day == 0 and WARM_UP > 0:
            warm_up_end = OPEN_TIME + WARM_UP
            env.run(until=warm_up_end)
            stats.reset()          # reset only stats after warm-up
            env.run(until=CLOSE_TIME)
        else:
            env.run(until=CLOSE_TIME)

    # ---- KPIs (one number per KPI) ----
    total = getattr(stats, "total_customers", 0)
    abandoned = getattr(stats, "abandoned_customers", 0)
    abandonment_rate = (abandoned / total) if total > 0 else 0.0

    cashier_p95 = stats.p95_cashier_wait()
    scooper_p95 = stats.p95_scooper_wait()

    # Utilization based on steady-time (open minutes * days minus warm-up once)
    OPEN_MINUTES_PER_DAY = CLOSE_TIME - OPEN_TIME
    steady_time = (OPEN_MINUTES_PER_DAY * DAYS) - WARM_UP
    utilizations = {}
    for res, busy in stats.resource_busy_time.items():
        utilizations[res] = (busy / steady_time) if steady_time > 0 else 0.0

    return {
        "abandonment_rate": abandonment_rate,
        "cashier_p95": cashier_p95,
        "scooper_p95": scooper_p95,
        "utilizations": utilizations,
        "total_customers": total,
    }


# --------------------------
# Many replications
# --------------------------
def run_many_replications(N=20, seed0=100):
    results = []
    for i in range(N):
        results.append(run_one_replication(seed=seed0 + i))
    return results


# --------------------------
# MAIN: orchestrate + CIs
# --------------------------
def main():
    N = 20
    reps = run_many_replications(N=N, seed0=100)

    # Abandonment rate CI
    aband = [r["abandonment_rate"] for r in reps]
    m, lo, hi = mean_ci_95(aband)
    print(f"\nReplications: {N}")
    print(f"Abandonment rate: mean={m:.4f} | 95% CI [{lo:.4f}, {hi:.4f}]")

    # Cashier p95 CI
    cashier_p95s = [r["cashier_p95"] for r in reps]
    m, lo, hi = mean_ci_95(cashier_p95s)
    print(f"Cashier p95 wait (min): mean={m:.3f} | 95% CI [{lo:.3f}, {hi:.3f}]")

    # Scooper p95 CI
    scooper_p95s = [r["scooper_p95"] for r in reps]
    m, lo, hi = mean_ci_95(scooper_p95s)
    print(f"Scooper p95 wait (min): mean={m:.3f} | 95% CI [{lo:.3f}, {hi:.3f}]")

    # Utilization CI per resource
    # (take resource names from first replication)
    print("\nUtilization (per resource):")
    res_names = list(reps[0]["utilizations"].keys()) if reps else []
    for res in res_names:
        vals = [r["utilizations"].get(res, 0.0) for r in reps]
        m, lo, hi = mean_ci_95(vals)
        print(f"  {res}: mean={m:.2%} | 95% CI [{lo:.2%}, {hi:.2%}]")

    # ---- Average total arrivals CI ----
    arrivals = [r["total_customers"] for r in reps]
    m, lo, hi = mean_ci_95(arrivals)

    print(
        f"Total arrivals per run: mean={m:.1f} "
        f"| 95% CI [{lo:.1f}, {hi:.1f}]"
    )



if __name__ == "__main__":
    main()
