"""Smart Expense Tracker - a beginner-friendly Flask web app."""
import csv
import io
import os
from datetime import date

import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend so we can render charts on a server.
import matplotlib.pyplot as plt
from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-change-me")

# Path to the CSV file that stores all expenses.
CSV_FILE = os.path.join(os.path.dirname(__file__), "expenses.csv")
CSV_HEADERS = ["Date", "Category", "Amount", "Description"]
CATEGORIES = ["Food", "Travel", "Bills", "Entertainment", "Other"]


def ensure_csv_exists():
    """Create the CSV file with headers if it does not yet exist."""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def read_expenses():
    """Read all expenses from the CSV file and return a list of dicts.

    Each expense gets an `index` key matching its row position in the CSV
    (0-based, excluding the header). We use this index for deletion.
    """
    ensure_csv_exists()
    expenses = []
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                row["Amount"] = float(row["Amount"])
            except (ValueError, TypeError):
                continue
            row["index"] = i
            expenses.append(row)
    return expenses


def write_expense(date_str, category, amount, description):
    """Append a new expense row to the CSV file."""
    ensure_csv_exists()
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([date_str, category, f"{amount:.2f}", description])


def delete_expense(index):
    """Delete the expense at the given row index and rewrite the CSV."""
    expenses = read_expenses()
    kept = [e for e in expenses if e["index"] != index]
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for e in kept:
            writer.writerow([e["Date"], e["Category"], f"{e['Amount']:.2f}", e["Description"]])


@app.route("/")
def welcome():
    """Animated welcome / splash page. Click anywhere to enter the dashboard."""
    return render_template("welcome.html")


@app.route("/dashboard")
def home():
    """Dashboard: show totals, top category, top month, and recent expenses."""
    expenses = read_expenses()
    total = sum(e["Amount"] for e in expenses)

    # Find the category with the highest total spending.
    category_totals = {}
    for e in expenses:
        category_totals[e["Category"]] = category_totals.get(e["Category"], 0) + e["Amount"]
    top_category = max(category_totals, key=category_totals.get) if category_totals else None

    # Find the month with the highest total spending.
    monthly_totals = {}
    for e in expenses:
        month = e["Date"][:7]
        monthly_totals[month] = monthly_totals.get(month, 0) + e["Amount"]
    top_month = max(monthly_totals, key=monthly_totals.get) if monthly_totals else None
    top_month_total = monthly_totals[top_month] if top_month else 0

    # Show the 5 most recent expenses (last rows in the CSV).
    recent = list(reversed(expenses[-5:]))

    return render_template(
        "home.html",
        total=total,
        top_category=top_category,
        top_month=top_month,
        top_month_total=top_month_total,
        recent=recent,
        has_data=bool(expenses),
    )


@app.route("/add", methods=["GET", "POST"])
def add_expense():
    """Form to add a new expense; saves it and redirects home with a flash."""
    if request.method == "POST":
        date_str = request.form.get("date", "").strip()
        category = request.form.get("category", "").strip()
        amount_raw = request.form.get("amount", "").strip()
        description = request.form.get("description", "").strip()

        try:
            amount = float(amount_raw)
        except ValueError:
            flash("Please enter a valid number for amount.", "error")
            return redirect(url_for("add_expense"))

        if not date_str or category not in CATEGORIES:
            flash("Please fill in all fields correctly.", "error")
            return redirect(url_for("add_expense"))

        write_expense(date_str, category, amount, description)
        flash("Expense added successfully!", "success")
        return redirect(url_for("home"))

    return render_template(
        "add.html",
        today=date.today().isoformat(),
        categories=CATEGORIES,
    )


@app.route("/delete/<int:index>", methods=["POST"])
def delete(index):
    """Delete an expense and return to the page the user came from."""
    delete_expense(index)
    flash("Expense deleted.", "success")
    # Send the user back to wherever they were (defaults to home).
    return redirect(request.referrer or url_for("home"))


@app.route("/view")
def view_all():
    """Display every expense in a table."""
    expenses = read_expenses()
    return render_template("view.html", expenses=expenses)


@app.route("/summary")
def monthly_summary():
    """Group spending by month (YYYY-MM) and display totals."""
    expenses = read_expenses()
    monthly = {}
    for e in expenses:
        month = e["Date"][:7]
        monthly[month] = monthly.get(month, 0) + e["Amount"]

    rows = sorted(monthly.items())
    return render_template("summary.html", rows=rows)


@app.route("/export/expenses.csv")
def export_expenses():
    """Download the full list of expenses as a CSV file."""
    ensure_csv_exists()
    return send_file(
        CSV_FILE,
        mimetype="text/csv",
        as_attachment=True,
        download_name="expenses.csv",
    )


@app.route("/export/summary.csv")
def export_summary():
    """Download the monthly summary as a CSV file."""
    expenses = read_expenses()
    monthly = {}
    for e in expenses:
        month = e["Date"][:7]
        monthly[month] = monthly.get(month, 0) + e["Amount"]

    # Build the CSV in memory.
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Month", "Total"])
    for month, total in sorted(monthly.items()):
        writer.writerow([month, f"{total:.2f}"])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=monthly_summary.csv"},
    )


@app.route("/charts")
def charts():
    """Page that embeds the two chart images."""
    expenses = read_expenses()
    return render_template("charts.html", has_data=bool(expenses))


def _png_response(fig):
    """Helper to turn a matplotlib figure into a PNG Flask Response."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/png")


@app.route("/chart/pie.png")
def chart_pie():
    """Generate a pie chart showing spending broken down by category."""
    expenses = read_expenses()
    category_totals = {}
    for e in expenses:
        category_totals[e["Category"]] = category_totals.get(e["Category"], 0) + e["Amount"]

    fig, ax = plt.subplots(figsize=(6, 6))
    if category_totals:
        labels = list(category_totals.keys())
        values = list(category_totals.values())
        colors = ["#7FB3D5", "#F5B041", "#82E0AA", "#F1948A", "#BB8FCE"]
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90,
               colors=colors[: len(labels)])
        ax.set_title("Spending by Category")
    else:
        ax.text(0.5, 0.5, "No expenses yet", ha="center", va="center", fontsize=14)
        ax.axis("off")
    return _png_response(fig)


@app.route("/chart/bar.png")
def chart_bar():
    """Generate a bar chart showing total spending per month (in rupees)."""
    expenses = read_expenses()
    monthly = {}
    for e in expenses:
        month = e["Date"][:7]
        monthly[month] = monthly.get(month, 0) + e["Amount"]

    fig, ax = plt.subplots(figsize=(8, 5))
    if monthly:
        months = sorted(monthly.keys())
        totals = [monthly[m] for m in months]
        ax.bar(months, totals, color="#5DADE2")
        ax.set_title("Monthly Spending")
        ax.set_xlabel("Month")
        ax.set_ylabel("Amount (Rs.)")
        plt.xticks(rotation=45, ha="right")
    else:
        ax.text(0.5, 0.5, "No expenses yet", ha="center", va="center", fontsize=14)
        ax.axis("off")
    return _png_response(fig)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
