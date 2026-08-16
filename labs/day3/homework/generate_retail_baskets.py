"""
Generate a small synthetic retail-transaction dataset for the Day 3
market-basket homework.

This set is deliberately *natively transactional*: one row per (basket_id,
item), with genuine product associations planted in. It contrasts with the
in-session portal exercise, where baskets have to be constructed from a
non-transactional dataset and the resulting rules are weak. Here the rules are
strong and interpretable, so delegates see what market basket analysis looks
like when the data actually fits the technique.

Licence-clean: fully synthetic, fixed seed, reproducible. UK English throughout.
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(2026)
N_BASKETS = 4000

HERE = Path(__file__).resolve().parent
OUT = HERE / "retail"
OUT.mkdir(parents=True, exist_ok=True)

# A small, familiar product range
PRODUCTS = [
    "Bread", "Butter", "Milk", "Eggs", "Pasta", "Tomato Sauce", "Cheese",
    "Soft Drinks", "Crisps", "Nappies", "Baby Wipes", "Coffee", "Sugar", "Tea", "Bananas",
]

# Planted associations: (item_a, item_b, probability b is added when a is present).
# These are the rules a delegate should recover with a decent lift.
PLANTED = [
    ("Bread", "Butter", 0.60),
    ("Pasta", "Tomato Sauce", 0.65),
    ("Soft Drinks", "Crisps", 0.55),
    ("Nappies", "Baby Wipes", 0.70),
    ("Coffee", "Sugar", 0.50),
    ("Tea", "Milk", 0.45),
]


def make_basket():
    """One shopping basket: a random core, then planted co-purchases layered on."""
    size = RNG.integers(2, 7)
    items = set(RNG.choice(PRODUCTS, size=size, replace=False))
    for a, b, p in PLANTED:
        if a in items and RNG.random() < p:
            items.add(b)
        # weaker reverse pull, so the rule is asymmetric like real baskets
        if b in items and RNG.random() < p * 0.5:
            items.add(a)
    return sorted(items)


rows = []
for bid in range(1, N_BASKETS + 1):
    for item in make_basket():
        rows.append({"basket_id": bid, "item": item})

df = pd.DataFrame(rows)
df.to_csv(OUT / "retail_transactions.csv", index=False)

n_items = df.groupby("basket_id")["item"].size()
print(f"Baskets: {df['basket_id'].nunique():,}")
print(f"Rows (basket-item pairs): {len(df):,}")
print(f"Average basket size: {n_items.mean():.1f}")
print(f"Distinct products: {df['item'].nunique()}")
print("Wrote to:", OUT / "retail_transactions.csv")
