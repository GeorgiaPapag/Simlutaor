from dataclasses import dataclass

@dataclass
class Customer:
    id: int
    arrival_time: float
    is_seated: bool


# from Customer import Customer

# c = Customer(1, 0.0, True)
# print(c)
