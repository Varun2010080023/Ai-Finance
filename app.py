from datetime import date, datetime
from typing import List

import math
import pandas as pd
import plotly.express as px
import streamlit as st

from finance_ai.calculations import (
    FutureExpense,
    MonthlyRecord,
    build_future_expense_plan,
    compute_total_gap,
    required_emergency_fund,
    summarize_cash_flow,
)
from finance_ai.forecast import forecast_expenses

st.set_page_config(page_title="AI Finance Planner", page_icon="AI", layout="wide")

st.title("AI Finance Planner")
st.write(
    """Plan ahead for upcoming expenses, understand your cash flow, and see how much you
    need to save each month to stay on track."""
)



def _add_months(base: date, months: int) -> date:
    year = base.year + (base.month - 1 + months) // 12
    month = (base.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def _normalize_category(value: object) -> str:
    if value is None:
        return "Other"
    normalized = str(value).strip().lower()
    mapping = {
        "essential": "Essential",
        "discretionary": "Discretionary",
        "other": "Other",
        "savings": "Savings",
    }
    return mapping.get(normalized, "Other")


def _default_breakdown() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"name": "Rent", "amount": 1500.0, "category": "Essential"},
            {"name": "Groceries", "amount": 500.0, "category": "Essential"},
            {"name": "Dining out", "amount": 250.0, "category": "Discretionary"},
            {"name": "Streaming services", "amount": 60.0, "category": "Other"},
        ]
    )


def _aggregate_breakdown(df: pd.DataFrame) -> dict:
    totals = {"Essential": 0.0, "Discretionary": 0.0, "Other": 0.0, "Savings": 0.0}
    for _, row in df.iterrows():
        amount = float(row.get("amount", 0.0) or 0.0)
        if amount <= 0:
            continue
        category = _normalize_category(row.get("category"))
        totals.setdefault(category, 0.0)
        totals[category] += amount
    totals["total"] = totals["Essential"] + totals["Discretionary"] + totals["Other"] + totals["Savings"]
    return totals


def _collect_breakdown_entries(df: pd.DataFrame) -> List[dict]:
    entries: List[dict] = []
    for _, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        amount = float(row.get("amount", 0.0) or 0.0)
        if not name or amount <= 0:
            continue
        category = _normalize_category(row.get("category"))
        entries.append({"name": name, "category": category, "amount": amount})
    return entries


def _default_history(
    monthly_income: float,
    essential_expenses: float,
    discretionary_expenses: float,
    other_expenses: float,
    current_savings: float,
) -> pd.DataFrame:
    today = date.today().replace(day=1)
    periods = pd.date_range(end=pd.Timestamp(today), periods=6, freq="MS")
    rows = []
    for idx, period in enumerate(periods):
        trend_adjust = 0.96 + idx * 0.015
        discretionary_adjust = 0.88 + idx * 0.02
        rows.append(
            {
                "month": period.strftime("%Y-%m"),
                "income": monthly_income,
                "essential": essential_expenses * trend_adjust,
                "discretionary": discretionary_expenses * discretionary_adjust,
                "other": other_expenses,
                "savings": max(current_savings, 0.0) / 10.0,
            }
        )
    return pd.DataFrame(rows)


st.header("1. Monthly Expense Breakdown")
st.write(
    "Use the breakdown table to list recurring expenses and the historical editor to refine your trends."
)
breakdown_df = st.data_editor(
    _default_breakdown(),
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "category": st.column_config.SelectboxColumn(
            "Category",
            options=["Essential", "Discretionary", "Other"],
        ),
        "amount": st.column_config.NumberColumn("Amount", min_value=0.0, step=50.0),
    },
    key="breakdown_table",
)

breakdown_totals = _aggregate_breakdown(breakdown_df)
breakdown_entries = _collect_breakdown_entries(breakdown_df)

if breakdown_totals["total"] > 0:
    st.caption(f"Total detailed expenses captured: ${breakdown_totals['total']:,.0f}")

st.header("2. Current Snapshot")
col_income, col_balance = st.columns(2)
with col_income:
    monthly_income = st.number_input("Average monthly income", min_value=0.0, value=5000.0, step=100.0)
with col_balance:
    current_savings = st.number_input("Current savings balance", min_value=0.0, value=2000.0, step=100.0)

col_exp1, col_exp2, col_exp3 = st.columns(3)
with col_exp1:
    essential_expenses = st.number_input("Essential expenses", min_value=0.0, value=2500.0, step=50.0)
with col_exp2:
    discretionary_expenses = st.number_input("Discretionary expenses", min_value=0.0, value=800.0, step=50.0)
with col_exp3:
    other_expenses = st.number_input("Other recurring expenses", min_value=0.0, value=200.0, step=50.0)

history_df = st.data_editor(
    _default_history(
        monthly_income,
        essential_expenses,
        discretionary_expenses,
        other_expenses,
        current_savings,
    ),
    num_rows="dynamic",
    use_container_width=True,
    key="history_table",
)
st.header("3. Future Expenses & Goals")


def _default_future_expenses() -> pd.DataFrame:
    today = date.today().replace(day=1)
    return pd.DataFrame(
        [
            {
                "name": "Insurance premium",
                "amount": 1200.0,
                "due_date": _add_months(today, 3),
                "priority": "High",
            },
            {
                "name": "Holiday trip",
                "amount": 1800.0,
                "due_date": _add_months(today, 7),
                "priority": "Medium",
            },
        ]
    )


future_expense_df = st.data_editor(
    _default_future_expenses(),
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "due_date": st.column_config.DateColumn("Due date"),
    },
    key="future_table",
)


def _to_monthly_records(df: pd.DataFrame) -> List[MonthlyRecord]:
    records: List[MonthlyRecord] = []
    for _, row in df.iterrows():
        month_value = str(row.get("month", "")).strip()
        if not month_value:
            continue
        try:
            period_date = datetime.strptime(month_value + "-01", "%Y-%m-%d").date()
        except ValueError:
            continue
        records.append(
            MonthlyRecord(
                period=period_date,
                income=float(row.get("income", 0.0) or 0.0),
                essential_expenses=float(row.get("essential", 0.0) or 0.0),
                discretionary_expenses=float(row.get("discretionary", 0.0) or 0.0),
                other_expenses=float(row.get("other", 0.0) or 0.0),
                savings_contribution=float(row.get("savings", 0.0) or 0.0),
            )
        )
    return records


def _to_future_expenses(df: pd.DataFrame) -> List[FutureExpense]:
    expenses: List[FutureExpense] = []
    for _, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        due = row.get("due_date")
        if isinstance(due, str):
            try:
                due_date = datetime.strptime(due, "%Y-%m-%d").date()
            except ValueError:
                continue
        elif isinstance(due, pd.Timestamp):
            due_date = due.date()
        elif isinstance(due, date):
            due_date = due
        else:
            continue
        expenses.append(
            FutureExpense(
                name=name,
                amount=float(row.get("amount", 0.0) or 0.0),
                due_date=due_date,
                priority=str(row.get("priority", "Medium")),
            )
        )
    return expenses


if st.button("Analyse my plan", type="primary"):
    monthly_records = _to_monthly_records(history_df)
    if monthly_records:
        summary = summarize_cash_flow(monthly_records)
        avg_surplus = summary["avg_income"] - summary["avg_total_expenses"]
    else:
        if breakdown_totals["total"] > 0:
            base_essential = breakdown_totals["Essential"]
            base_discretionary = breakdown_totals["Discretionary"]
            base_other = breakdown_totals["Other"]
        else:
            base_essential = essential_expenses
            base_discretionary = discretionary_expenses
            base_other = other_expenses
        total_estimated_expenses = base_essential + base_discretionary + base_other
        avg_surplus = monthly_income - total_estimated_expenses
        summary = {
            "months": 0,
            "avg_income": monthly_income,
            "avg_total_expenses": total_estimated_expenses,
            "avg_essential": base_essential,
            "avg_discretionary": base_discretionary,
            "avg_other": base_other,
            "avg_savings": 0.0,
            "avg_net": avg_surplus,
        }

    future_expenses = _to_future_expenses(future_expense_df)
    if not future_expenses:
        st.warning("Add at least one future expense to create a plan.")
    else:
        plan = build_future_expense_plan(
            current_balance=current_savings,
            average_monthly_surplus=avg_surplus,
            future_expenses=future_expenses,
        )
        gap = compute_total_gap(plan, avg_surplus)

        st.subheader("Cash Flow Snapshot")
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        metric_col1.metric("Avg income", f"${summary['avg_income']:,.0f}")
        metric_col2.metric("Avg expenses", f"${summary['avg_total_expenses']:,.0f}")
        metric_col3.metric("Avg surplus", f"${avg_surplus:,.0f}")
        emergency_target = required_emergency_fund(summary["avg_essential"])
        metric_col4.metric("Emergency fund target", f"${emergency_target:,.0f}")
        savings_rate = avg_surplus / summary["avg_income"] if summary["avg_income"] else 0.0
        metric_col5.metric("Savings rate", f"{savings_rate * 100:.0f}%")

        if avg_surplus < 0:
            st.error("Your average expenses exceed income. Reduce spending or increase income to stay on track.")

        st.subheader("Savings Plan")
        plan_df = pd.DataFrame(plan)
        plan_df["readiness"] = plan_df["readiness_ratio"].apply(lambda r: f"{r * 100:.0f}%")
        st.dataframe(
            plan_df[
                [
                    "name",
                    "priority",
                    "due_date",
                    "months_to_goal",
                    "amount",
                    "allocated_from_balance",
                    "remaining_goal",
                    "suggested_monthly_contribution",
                    "readiness",
                ]
            ],
            use_container_width=True,
        )

        st.info(
            f"Total outstanding goals: ${gap['total_remaining_goal']:,.0f} | "
            f"Potential savings capacity: ${gap['savings_capacity']:,.0f} | "
            f"Gap to close: ${gap['savings_gap']:,.0f}"
        )

        named_expenses = [entry for entry in breakdown_entries if entry["category"] != "Savings"]

        insights: List[str] = []
        named_expense_total = sum(entry["amount"] for entry in named_expenses)
        if named_expense_total > 0:
            top_expense = max(named_expenses, key=lambda entry: entry["amount"])
            top_share = (top_expense["amount"] / named_expense_total) * 100
            insights.append(
                f"{top_expense['name']} is your largest tracked expense at {top_share:.0f}% of named spending."
            )
        elif breakdown_totals["total"] > 0:
            insights.append("Capture more named expenses to tailor your spending insights.")

        if avg_surplus < 0:
            insights.append("Monthly deficit detected - trim spending or raise income to balance cash flow.")

        if summary["avg_income"] > 0 and 0 <= savings_rate < 0.15:
            insights.append("Your savings rate is under 15%; consider trimming discretionary spend or boosting income.")

        if gap["savings_gap"] > 0:
            insights.append(
                f"You need an additional ${gap['savings_gap']:,.0f} to fund every goal before its due date."
            )
        elif gap["total_remaining_goal"] > 0 and avg_surplus > 0:
            months_to_clear = math.ceil(gap["total_remaining_goal"] / max(avg_surplus, 1e-9))
            insights.append(
                f"At your current surplus you could fund the remaining ${gap['total_remaining_goal']:,.0f} "
                f"in about {months_to_clear} month(s)."
            )

        due_soon = [item for item in plan if item["months_to_goal"] <= 3 and item["remaining_goal"] > 0]
        if due_soon:
            urgent = min(due_soon, key=lambda item: item["months_to_goal"])
            insights.append(
                f"{urgent['name']} is due in {urgent['months_to_goal']} month(s) and still needs "
                f"${urgent['remaining_goal']:,.0f}."
            )

        if not insights:
            insights.append("You're on track - keep monitoring your plan each month.")

        st.subheader("Insights & next steps")
        for note in insights:
            st.markdown(f"- {note}")


        st.subheader("Visual breakdowns")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            if named_expenses:
                detail_df = pd.DataFrame(named_expenses)
                expense_fig = px.pie(detail_df, values="amount", names="name", title="Monthly expense breakdown")
                expense_fig.update_traces(textposition="inside", textinfo="label+percent")
                st.plotly_chart(expense_fig, use_container_width=True)
            else:
                expense_data = pd.DataFrame(
                    {
                        "Category": ["Essential", "Discretionary", "Other", "Savings"],
                        "Amount": [
                            max(summary["avg_essential"], 0.0),
                            max(summary["avg_discretionary"], 0.0),
                            max(summary["avg_other"], 0.0),
                            max(summary["avg_savings"], 0.0),
                        ],
                    }
                )
                expense_data = expense_data[expense_data["Amount"] > 0]
                if expense_data.empty:
                    st.write("Enter expense amounts to view the allocation breakdown.")
                else:
                    expense_fig = px.pie(expense_data, values="Amount", names="Category", title="Average monthly allocation")
                    expense_fig.update_traces(textposition="inside", textinfo="label+percent")
                    st.plotly_chart(expense_fig, use_container_width=True)

        with chart_col2:
            goal_data = plan_df[["name", "remaining_goal", "amount"]].copy()
            goal_data["remaining_goal"] = goal_data["remaining_goal"].clip(lower=0)
            remaining = goal_data[goal_data["remaining_goal"] > 0]
            value_field = "remaining_goal"
            title = "Remaining goal distribution"
            if remaining.empty:
                remaining = goal_data[goal_data["amount"] > 0]
                value_field = "amount"
                title = "Goal amount distribution"
            if remaining.empty:
                st.write("Add goal amounts to see how your targets are distributed.")
            else:
                goal_fig = px.pie(remaining, values=value_field, names="name", title=title)
                goal_fig.update_traces(textposition="inside", textinfo="label+percent")
                st.plotly_chart(goal_fig, use_container_width=True)

        st.subheader("Expense trend and forecast")
        if monthly_records:
            history = pd.DataFrame(
                {
                    "period": [record.period for record in monthly_records],
                    "total_expenses": [record.total_expenses for record in monthly_records],
                }
            ).sort_values("period")
            future_forecast = forecast_expenses(monthly_records, periods_ahead=6)
            forecast_df = pd.DataFrame(
                {
                    "period": [item[0] for item in future_forecast],
                    "total_expenses": [max(item[1], 0.0) for item in future_forecast],
                }
            )
            combined = pd.concat([
                history.assign(type="Actual"),
                forecast_df.assign(type="Forecast"),
            ])
            chart_data = combined.pivot_table(
                index="period",
                columns="type",
                values="total_expenses",
            ).sort_index()
            st.line_chart(chart_data)
        else:
            st.write("Add historical data to see expense forecasts.")

st.caption(
    "This tool uses a simple linear model to estimate expense trends. Use it as a guide, "
    "not a substitute for personalised financial advice."
)
