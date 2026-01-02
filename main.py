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



# πάμε λοιπόν στο επόμενο στάδιο της εκφώνησης αν θεωρείς ότι με τα υπόλοιπα έχουμε τελειώσει
# Ζητούμενα & στόχοι 
# • Κύριος στόχος: μείωση ποσοστού δυσαρεστημένων (abandonments 
# λόγω αναμονής > 12′) κάτω από 5%. 
# • Δευτερεύοντες: 
# o 95ο εκατοστημόριο αναμονής ταμείου < 6′, 
# o 95ο εκατοστημόριο αναμονής scooping < 5′, 
# o μέση αξιοποίηση βασικών πόρων (barista, scooper, ταμίας, 
# σερβιτόρος) εντός λογικών ορίων (π.χ. 70–85%).