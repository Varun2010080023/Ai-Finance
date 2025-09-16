# AI Finance Planner

Interactive Streamlit app that lets you model monthly cash flow, forecast expenses with a
simple machine learning trend, and translate upcoming obligations into an actionable saving plan.

## Features
- Capture monthly income and spending patterns with an editable table
- Break down recurring expenses by name for personalised visuals
- Forecast future expense trends with a linear regression model
- Enter upcoming expenses and receive required monthly saving contributions
- Compare saving capacity versus required goals and highlight shortfalls
- Visualise actual vs forecast expense trajectory
- See automated savings-rate metrics and next-step recommendations
- Inspect spending and goal mix with interactive pie charts

## Getting started
1. Ensure Python 3.9 or newer is installed.
2. Create and activate a virtual environment (recommended):
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Run the app
Launch Streamlit and open the local browser session:
```powershell
streamlit run app.py
```

The interface ships with example data that you can overwrite. Fill out your current monthly
figures, adjust historical months if you have more detail, and list upcoming expenses with
target dates. Click **Analyse my plan** to generate a savings strategy, emergency fund
recommendations, and a forecast chart.

> This tool offers guidance only and should not replace advice from a licensed financial
professional.
