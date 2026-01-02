from dataclasses import dataclass, field
from typing import Dict, Tuple, List

@dataclass
class SimTimeConfig:
    # store operations (in minutes form 00:00)
    OPEN_TIME: int = 7 * 60 # 07:00 
    CLOSE_TIME: int = 23 * 60 # 23:00

    # simulation
    WARM_UP_TIME: int = 60
    RUN_LENGTH_DAYS: int = 14 # ≥ 14 days

    # calculate the hours the store is open
    @property
    def DAY_LENGTH(self) -> int:
        return self.CLOSE_TIME - self.OPEN_TIME
    
# customer arrivals
@dataclass
class ArrivalConfig:
    # Ρυθμοί αφίξεων (μέσος χρόνος μεταξύ αφίξεων σε λεπτά)
    OFF_PEAK_MEAN: float = 6.0
    PEAK_MEAN: float = 2.5

    # Παράθυρα αιχμής (σε λεπτά από 00:00)
    PEAK_START: int = 15 * 60        # 15:00
    PEAK_END: int = 22 * 60          # 22:00

# customer consumption choice
@dataclass
class ConsumptionConfig:
    SEATED_PROB: float = 0.40   # 40% καθιστοί
    #TAKE_AWAY_PROB: float = 0.60 # 60% take away

# initial choices in orders
@dataclass
class OrderChoiceConfig:
    INITIAL_ORDER_PROBS: Dict[str, float] = None

    def __post_init__(self):
        self.INITIAL_ORDER_PROBS = {
            "ice_cream": 0.43,
            "waffle": 0.14,          # waffle + ice cream
            "milkshake": 0.16,
            "coffee": 0.23,
            "toppings": 0.02,
            "small_purchase": 0.02,
        }

@dataclass
class ContinuationConfig:
    CONTINUATION_PROBS: Dict[str, Dict[str, float]] = None

    def __post_init__(self):
        self.CONTINUATION_PROBS = {
            "ice_cream": {
                "toppings": 0.35,
                "milkshake": 0.06,
                "coffee": 0.08,
                "pay": 0.51,
            },
            "waffle": {
                "ice_cream": 1.00,   # υποχρεωτικό
            },
            # παγωτό ΜΕΤΑ από βάφλα
            "ice_cream_after_waffle": {
                "toppings": 0.45,
                "pay": 0.55,
            },
            "milkshake": {
                "ice_cream": 0.12,
                "toppings": 0.08,
                "coffee": 0.10,
                "pay": 0.70,
            },
            "coffee": {
                "ice_cream": 0.10,
                "toppings": 0.05,
                "pay": 0.85,
            },
            "toppings": {
                "pay": 1.00,
            },
            "small_purchase": {
                "pay": 1.00,
            },
        }

@dataclass
class IceCreamConfig:
    SCOOPS_PROBS: Dict[int, float] = None

    def __post_init__(self):
        self.SCOOPS_PROBS = {
            1: 0.40,
            2: 0.45,
            3: 0.15,
        }

# uniforms
@dataclass
class ServiceTimeConfig:
    # (min, max) ή (mean, std)

    ORDER: Tuple[float, float] = (0.5, 1.2)          # uniform
    PAYMENT: Tuple[float, float] = (0.7, 0.2)        # normal

    ICE_CREAM_PER_SCOOP: Tuple[float, float] = (0.4, 0.2)
    WAFFLE: Tuple[float, float] = (3.0, 0.5)
    MILKSHAKE: Tuple[float, float] = (2.8, 0.7)
    COFFEE: Tuple[float, float] = (1.2, 0.3)
    TOPPINGS: Tuple[float, float] = (0.8, 0.3)

    SERVING: Tuple[float, float] = (0.6, 1.4)        # uniform
    CONSUMPTION: Tuple[float, float] = (10.0, 3.0)   # normal
    TABLE_CLEANING: Tuple[float, float] = (0.5, 1.0)

# waiting
@dataclass
class WaitingRulesConfig:
    MAX_QUEUE_WAIT: int = 12.0      # λεπτά
    MAX_TABLE_WAIT: int = 5.0      # λεπτά

# resources px employers
@dataclass
class ResourceConfig:
    CASHIERS: int = 1
    SCOOPERS: int = 1
    WAFFLE_MAKERS: int = 1
    BARISTAS: int = 1
    TOPPINGS_STAFF: int = 1
    WAITERS: int = 1

    TABLES: int = 8


@dataclass
class SimulationConfig:
    time: SimTimeConfig = field(default_factory=SimTimeConfig)
    arrivals: ArrivalConfig = field(default_factory=ArrivalConfig)
    order_choices: OrderChoiceConfig = field(default_factory=OrderChoiceConfig)
    continuations: ContinuationConfig = field(default_factory=ContinuationConfig)
    consumption: ConsumptionConfig = field(default_factory=ConsumptionConfig)
    ice_cream: IceCreamConfig = field(default_factory=IceCreamConfig)  # 👈 ΝΕΟ
    service_times: ServiceTimeConfig = field(default_factory=ServiceTimeConfig)
    waiting_rules: WaitingRulesConfig = field(default_factory=WaitingRulesConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)
