import psycopg2
from psycopg2.extras import RealDictCursor
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def fetch_daily_customers(db_params, start, end):
    """Daily customers query"""
    query = """
        SELECT DATE(event_time) AS day,
            COUNT(DISTINCT user_id) AS num_customers
        from customers
        WHERE event_type = 'purchase'
            AND event_type >= %s AND event_time < %s
        GROUP BY day
        ORDER BY day;
    """
    return run_query(db_params, query, (start, end))


def fetch_monthly_sales(db_params, start, end):
    """Montly sales query"""
    query = """
        SELECT DATE_TRUNC('month', event_time) AS month,
            SUM(price) / 1000000 AS total_sales_millions
        FROM customers
        WHERE event_type = 'purchase'
            AND event_time >= %s AND event_time < %s
        GROUP BY month
        ORDER BY month;
    """
    return run_query(db_params, query, (start, end))


def fetch_daily_avg_spend(db_params, start, end):
    """Average daily spend query"""
    query = """
        SELECT DATE(event_time) AS day,
            SUM(price) / COUNT(DISTINCT user_id) AS avg_spend
        FROM customers
        WHERE event_type = 'purchase'
            AND event_time >= %s AND event_time < %s
        GROUP BY day
        ORDER BY day;
        """
    return run_query(db_params, query, (start, end))


def get_date_range():
    """Start and end date of database query"""
    return "2022-10-01", "2023-03-01"


def get_params():
    """Params of database"""
    return {
        "host": "localhost",
        "port": "5432",
        "dbname": "piscineds",
        "user": "jcologne",
        "password": "mysecretpassword",
    }


def run_query(db_params, query, params=None):
    """Run database query"""
    with psycopg2.connect(**db_params) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return rows


def plot_line_customers(rows, output_path):
    """Plot customers graph"""
    days = [r["day"] for r in rows]
    values = [r["num_customers"] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(days, values)
    ax.set_ylabel("Number of customers")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def plot_bar_monthly_sales(rows, output_path):
    """Plot monthly sales graph"""
    months = [r["month"].strftime("%b") for r in rows]
    values = [r["total_sales_millions"] for r in rows]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(months, values)
    ax.set_xlabel("month")
    ax.set_ylabel("total sales in millions of \u20b3")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def plot_area_avg_spend(rows, output_path):
    """Plot average spend graph"""
    days = [r["day"] for r in rows]
    values = [float(r["avg_spend"]) for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(days, values)
    ax.set_ylabel("average spend/customer in \u20b3")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def main():
    """Plot graphs of queryes"""
    db_params = get_params()
    dt_start, dt_end = get_date_range()

    daily_customers = fetch_daily_customers(db_params, dt_start, dt_end)
    plot_line_customers(daily_customers, "chart_customers_per_day.png")

    monthly_sales = fetch_monthly_sales(db_params, dt_start, dt_end)
    plot_bar_monthly_sales(monthly_sales, "chart_monthly_sales.png")

    daily_avg_spend = fetch_daily_avg_spend(db_params, dt_start, dt_end)
    plot_area_avg_spend(daily_avg_spend, "chart_avg_spend.png")


if __name__ == "__main__":
    main()
