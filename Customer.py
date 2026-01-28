from dataclasses import dataclass

@dataclass
class Customer:
    id: int
    arrival_time: float
    is_seated: bool