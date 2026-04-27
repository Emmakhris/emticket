from __future__ import annotations

# ITIL impact × urgency → priority matrix
# Rows = impact (1=Low → 4=Critical), Cols = urgency (1=Low → 4=Immediate)
# Values = Priority (1=P1-Critical → 4=P4-Low)
_PRIORITY_MATRIX = {
    (1, 1): 4, (1, 2): 4, (1, 3): 3, (1, 4): 3,
    (2, 1): 4, (2, 2): 3, (2, 3): 2, (2, 4): 2,
    (3, 1): 3, (3, 2): 2, (3, 3): 2, (3, 4): 1,
    (4, 1): 3, (4, 2): 2, (4, 3): 1, (4, 4): 1,
}


def calculate_priority(impact: int, urgency: int) -> int:
    """
    Returns a Priority integer (1=Critical, 2=High, 3=Medium, 4=Low)
    derived from the ITIL impact × urgency matrix.
    Defaults to P3 (Medium) for any unmapped combination.
    """
    return _PRIORITY_MATRIX.get((impact, urgency), 3)
