from collections import defaultdict
from datetime import date

from finances.model import Charge, Item, Order


def gather(
    items: list[Item], charges: list[Charge], since: date, until: date
) -> list[Order]:
    """Orders with a charge in the window, each with all its items and charges."""
    recent = {charge.order_id for charge in charges if since <= charge.date <= until}
    items_by, charges_by = defaultdict(list), defaultdict(list)
    for item in items:
        items_by[item.order_id].append(item)
    for charge in charges:
        charges_by[charge.order_id].append(charge)
    return [
        Order(order_id=order_id, items=items_by[order_id], charges=charges_by[order_id])
        for order_id in sorted(recent)
    ]
