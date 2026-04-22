# Smart Expense Tracker

A simple Flask web app to track personal expenses, with charts and CSV export.

## Features

- Animated welcome page (click anywhere to enter)
- Dashboard with total spending, top category, and top month
- Add / delete expenses
- View all expenses in a table
- Monthly summary with totals
- Pie + bar charts (rendered with matplotlib)
- Export expenses and summary as CSV
- All data stored in `expenses.csv` (no database required)

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000 in your browser.

## File structure

```
flask_app/
├── app.py              # Flask routes and logic
├── expenses.csv        # Data file (auto-created on first run)
├── requirements.txt
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── welcome.html
    ├── home.html       # Dashboard
    ├── add.html
    ├── view.html
    ├── summary.html
    └── charts.html
```
