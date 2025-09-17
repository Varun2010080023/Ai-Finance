from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Optional


@dataclass
class MonthlyRecord:
    """Represents a single month's high level cash flow."""

    period: date
    income: float
    essential_expenses: float
    discretionary_expenses: float
    other_expenses: float = 0.0
    savings_contribution: float = 0.0

    @property
    def total_expenses(self) -> float:
        return self.essential_expenses + self.discretionary_expenses + self.other_expenses

    @property
    def net_cash_flow(self) -> float:
        return self.income - self.total_expenses - self.savings_contribution


@dataclass
class FutureExpense:
    name: str
    amount: float
    due_date: date
    priority: str = "medium"


_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

def summarize_cash_flow(records: Iterable[MonthlyRecord]) -> dict:
    """Aggregate cash flow information from historical records."""

    records = list(records)
    if not records:
        raise ValueError("At least one monthly record is required to summarise cash flow")

    income_values = [r.income for r in records]
    essential_values = [r.essential_expenses for r in records]
    discretionary_values = [r.discretionary_expenses for r in records]
    other_values = [r.other_expenses for r in records]
    savings_values = [r.savings_contribution for r in records]
    total_expenses = [r.total_expenses for r in records]
    net_values = [r.net_cash_flow for r in records]

    months = len(records)

    return {
        "months": months,
        "avg_income": sum(income_values) / months,
        "avg_total_expenses": sum(total_expenses) / months,
        "avg_essential": sum(essential_values) / months,
        "avg_discretionary": sum(discretionary_values) / months,
        "avg_other": sum(other_values) / months,
        "avg_savings": sum(savings_values) / months,
        "avg_net": sum(net_values) / months,
    }


def required_emergency_fund(monthly_essential: float, months: int = 3) -> float:
    """Basic emergency fund recommendation."""

    return max(monthly_essential, 0.0) * max(months, 0)


def months_between(start: date, end: date) -> int:
    """Return the number of whole months between two dates, inclusive of the due month."""

    months = (end.year - start.year) * 12 + (end.month - start.month)
    return max(months, 0) + 1


def build_future_expense_plan(
    current_balance: float,
    average_monthly_surplus: float,
    future_expenses: Iterable[FutureExpense],
    start_date: Optional[date] = None,
) -> List[dict]:
    """Create a month-by-month saving plan for the supplied future expenses."""

    if start_date is None:
        start_date = date.today()

    def _sort_key(expense: FutureExpense) -> tuple[int, date]:
        priority_value = str(expense.priority or "").lower()
        priority_rank = _PRIORITY_RANK.get(priority_value, 3)
        return (priority_rank, expense.due_date)

    sorted_expenses = sorted(future_expenses, key=_sort_key)
    plan: List[dict] = []
    balance_remaining = max(current_balance, 0.0)

    for expense in sorted_expenses:
        months_to_due = months_between(start_date, expense.due_date)
        allocated_now = min(balance_remaining, expense.amount)
        balance_remaining -= allocated_now
        remaining_goal = max(expense.amount - allocated_now, 0.0)
        monthly_needed = remaining_goal / months_to_due if months_to_due > 0 else remaining_goal

        if average_monthly_surplus <= 0:
            readiness_ratio = 0.0 if remaining_goal > 0 else 1.0
        else:
            possible_savings = average_monthly_surplus * months_to_due
            readiness_ratio = min(possible_savings / remaining_goal, 1.0) if remaining_goal > 0 else 1.0

        plan.append(
            {
                "name": expense.name,
                "priority": expense.priority,
                "due_date": expense.due_date,
                "months_to_goal": months_to_due,
                "amount": expense.amount,
                "allocated_from_balance": allocated_now,
                "remaining_goal": remaining_goal,
                "suggested_monthly_contribution": monthly_needed,
                "readiness_ratio": readiness_ratio,
            }
        )

    return plan


def compute_total_gap(plan: Iterable[dict], average_monthly_surplus: float) -> dict:
    """Assess how feasible the plan is versus the surplus available."""

    plan = list(plan)
    total_required = sum(item["remaining_goal"] for item in plan)
    longest_months = max((item["months_to_goal"] for item in plan), default=0)
    savings_capacity = max(average_monthly_surplus, 0.0) * longest_months
    gap = max(total_required - savings_capacity, 0.0)

    return {
        "total_remaining_goal": total_required,
        "savings_capacity": savings_capacity,
        "savings_gap": gap,
    }
