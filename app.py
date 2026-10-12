from datetime import date
from flask import Flask, redirect, render_template, request, url_for
import sqlite3

app = Flask(__name__)


def get_db_connection():
  conn = sqlite3.connect("finances.db")
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  conn = get_db_connection()
  conn.execute(
      """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            payment_method TEXT,
            date TEXT
        )
    """
  )
  try:
    conn.execute("ALTER TABLE expenses ADD COLUMN date TEXT")
  except sqlite3.OperationalError:
    pass
  conn.commit()
  conn.close()


init_db()


@app.route("/", methods=["GET", "POST"])
def index():
  conn = get_db_connection()

  if request.method == "POST":
    amount = request.form["amount"]
    category = request.form["category"]
    description = request.form["description"]
    payment_method = request.form["payment_method"]
    expense_date = request.form["date"]

    conn.execute(
        """
            INSERT INTO expenses (amount, category, description, payment_method, date) 
            VALUES (?, ?, ?, ?, ?)
        """,
        (amount, category, description, payment_method, expense_date),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

  # Получаем параметры фильтров
  selected_category = request.args.get("category", "")
  filter_type = request.args.get(
      "filter_type", "all"
  )  # Режим фильтра по умолчанию
  date_day = request.args.get("date_day", "")
  date_month = request.args.get("date_month", "")
  date_start = request.args.get("date_start", "")
  date_end = request.args.get("date_end", "")

  categories = conn.execute(
      "SELECT DISTINCT category FROM expenses"
  ).fetchall()

  # Строим SQL-запрос динамически
  query = "SELECT * FROM expenses WHERE 1=1"
  params = []

  if selected_category:
    query += " AND category = ?"
    params.append(selected_category)

  # Применяем фильтр в зависимости от выбранного режима
  if filter_type == "day" and date_day:
    query += " AND date = ?"
    params.append(date_day)
  elif filter_type == "month" and date_month:
    query += " AND date LIKE ?"
    params.append(date_month + "%")
  elif filter_type == "range":
    if date_start and date_end:
      query += " AND date BETWEEN ? AND ?"
      params.append(date_start)
      params.append(date_end)
    elif date_start:
      query += " AND date >= ?"
      params.append(date_start)
    elif date_end:
      query += " AND date <= ?"
      params.append(date_end)

  query += " ORDER BY date DESC, id DESC"
  expenses = conn.execute(query, params).fetchall()

  # Запрос для подсчета общей суммы (аналогичный)
  total_query = "SELECT SUM(amount) FROM expenses WHERE 1=1"
  total_params = []
  if selected_category:
    total_query += " AND category = ?"
    total_params.append(selected_category)

  if filter_type == "day" and date_day:
    total_query += " AND date = ?"
    total_params.append(date_day)
  elif filter_type == "month" and date_month:
    total_query += " AND date LIKE ?"
    total_params.append(date_month + "%")
  elif filter_type == "range":
    if date_start and date_end:
      total_query += " AND date BETWEEN ? AND ?"
      total_params.append(date_start)
      total_params.append(date_end)
    elif date_start:
      total_query += " AND date >= ?"
      total_params.append(date_start)
    elif date_end:
      total_query += " AND date <= ?"
      total_params.append(date_end)

  total_result = conn.execute(total_query, total_params).fetchone()[0]
  total = total_result if total_result else 0

  # Данные для графика
  chart_query = (
      "SELECT category, SUM(amount) as total_amount FROM expenses WHERE 1=1"
  )
  chart_params = []
  if selected_category:
    chart_query += " AND category = ?"
    chart_params.append(selected_category)

  if filter_type == "day" and date_day:
    chart_query += " AND date = ?"
    chart_params.append(date_day)
  elif filter_type == "month" and date_month:
    chart_query += " AND date LIKE ?"
    chart_params.append(date_month + "%")
  elif filter_type == "range":
    if date_start and date_end:
      chart_query += " AND date BETWEEN ? AND ?"
      chart_params.append(date_start)
      chart_params.append(date_end)
    elif date_start:
      chart_query += " AND date >= ?"
      chart_params.append(date_start)
    elif date_end:
      chart_query += " AND date <= ?"
      chart_params.append(date_end)

  chart_query += " GROUP BY category"
  category_stats = conn.execute(chart_query, chart_params).fetchall()
  chart_labels = [row["category"] for row in category_stats]
  chart_data = [row["total_amount"] for row in category_stats]

  conn.close()
  today = date.today().isoformat()

  return render_template(
      "index.html",
      expenses=expenses,
      total=total,
      categories=categories,
      selected_category=selected_category,
      filter_type=filter_type,
      date_day=date_day,
      date_month=date_month,
      date_start=date_start,
      date_end=date_end,
      chart_labels=chart_labels,
      chart_data=chart_data,
      today=today,
  )


@app.route("/delete/<int:id>", methods=["POST"])
def delete_expense(id):
  conn = get_db_connection()
  conn.execute("DELETE FROM expenses WHERE id = ?", (id,))
  conn.commit()
  conn.close()
  return redirect(url_for("index"))


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
  conn = get_db_connection()
  if request.method == "POST":
    amount = request.form["amount"]
    category = request.form["category"]
    description = request.form["description"]
    payment_method = request.form["payment_method"]
    expense_date = request.form["date"]
    conn.execute(
        """
            UPDATE expenses 
            SET amount = ?, category = ?, description = ?, payment_method = ?, date = ? 
            WHERE id = ?
        """,
        (amount, category, description, payment_method, expense_date, id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

  expense = conn.execute(
      "SELECT * FROM expenses WHERE id = ?", (id,)
  ).fetchone()
  conn.close()
  return render_template("edit.html", expense=expense)


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)