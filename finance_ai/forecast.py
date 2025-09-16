from __future__ import annotations

from datetime import date
from typing import Iterable, List, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression

from .calculations import MonthlyRecord


def _prepare_features(records: List[MonthlyRecord]) -> Tuple[np.ndarray, np.ndarray]:
    X = np.arange(len(records)).reshape(-1, 1)
    y = np.array([record.total_expenses for record in records])
    return X, y


def forecast_expenses(
    records: Iterable[MonthlyRecord],
    periods_ahead: int = 6,
) -> List[Tuple[date, float]]:
    """Predict future monthly expenses using a simple linear trend."""

    records = list(records)
    if not records:
        raise ValueError("At least one monthly record is required to forecast expenses")

    if len(records) < 2:
        last_record = records[-1]
        return [
            (increment_month(last_record.period, i + 1), last_record.total_expenses)
            for i in range(periods_ahead)
        ]

    X, y = _prepare_features(records)
    model = LinearRegression()
    model.fit(X, y)

    last_index = len(records) - 1
    projections: List[Tuple[date, float]] = []
    for step in range(1, periods_ahead + 1):
        new_index = last_index + step
        forecast_value = float(model.predict(np.array([[new_index]]))[0])
        next_period = increment_month(records[-1].period, step)
        projections.append((next_period, forecast_value))

    return projections


def increment_month(current: date, months: int) -> date:
    year_offset, month = divmod(current.month - 1 + months, 12)
    new_year = current.year + year_offset
    new_month = month + 1
    day = min(current.day, 28)
    return date(new_year, new_month, day)
