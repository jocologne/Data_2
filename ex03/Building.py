import psycopg2
from psycopg2.extras import RealDictCursor
import matplotlib.pyplot as plt


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


def fetch_frequency(db_params):
    """Purchases for each client"""
    query = """
        SELECT user_id, COUNT(*) AS frequency
        FROM customers
        WHERE event_type = 'purchase'
        GROUP BY user_id
    """
    rows = run_query(db_params, query)
    return [float(r["frequency"]) for r in rows]


def fetch_spending(db_params):
    """Total spendin for each client"""
    query = """
        SELECT user_id, SUM(price) AS spending
        FROM customers
        WHERE event_type = 'purchase'
        GROUP BY user_id
    """
    rows = run_query(db_params, query)
    return [float(r["spending"]) for r in rows]


def plot_frequency(frequencies, output_path):
    """Plot frequency histogram graph"""
    fig, ax = plt.subplots(figsize=(6, 4))
    bins = range(0, int(max(frequencies)) + 10, 8)
    ax.hist(frequencies, bins=bins, edgecolor="white")
    ax.set_xlim(0, 40)
    ax.set_xlabel("frequency")
    ax.set_ylabel("customers")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def plot_spending(spending, output_path):
    """Plot spending histogram graph"""
    fig, ax = plt.subplots(figsize=(6, 4))
    bins = range(0, int(max(spending)) + 50, 15)
    ax.hist(spending, bins=bins, edgecolor="white")
    ax.set_xlim(0, 250)
    ax.set_xlabel("monetary value in \u20b3")
    ax.set_ylabel("customers")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def main():
    """Plot graphs for frequency and spending"""
    db_params = get_params()
    frequencies = fetch_frequency(db_params)
    plot_frequency(frequencies, "frequency.png")
    spending = fetch_spending(db_params)
    plot_spending(spending, "spending.png")


if __name__ == "__main__":
    main()
