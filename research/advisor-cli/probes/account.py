def withdraw(balance, amount):
    if amount >= balance:
        raise ValueError("insufficient")
    return balance - amount
