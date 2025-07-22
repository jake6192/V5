def compute_profit(quantity, price, cost_price):
    if price is None or cost_price is None:
        return 0.0
    return quantity * (price - cost_price)

def clamp_inventory(value):
    return max(0, int(value))

def is_valid_price(val):
    return isinstance(val, (int, float)) and val >= 0
