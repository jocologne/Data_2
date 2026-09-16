import psycopg2
from psycopg2.extras import RealDictCursor
import matplotlib.pyplot as plt


def get_db_params():
    """Databse params for connection"""
    return {
        "host": "localhost",
        "port": "5432",
        "dbname": "piscineds",
        "user": "jcologne",
        "password": "mysecretpassword",
    }


def run_query(db_params, query, params=None):
    """Run query received as parameter"""
    with psycopg2.connect(**db_params) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return rows


def fetch_price_stats(db_params):
    """Fetch price from database"""
    query = """
        SELECT
            COUNT(price) AS count,
            AVG(price) AS mean,
            STDDEV(price) AS std,
            MIN(price) AS min,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price) AS p25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price) AS p50,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price) AS p75,
            MAX(price) AS max
        FROM customers
        WHERE event_type = 'purchase';
    """
    return run_query(db_params, query)[0]


def fetch_avg_basket_per_user(db_params):
    """Fetch average price from database"""
    query = """
        WITH session_basket AS (
            SELECT user_id, user_session, SUM(price) AS basket_total
            FROM customers
            WHERE event_type = 'purchase'
            GROUP BY user_id, user_session
        )
        SELECT AVG(basket_total) AS avg_basket
        FROM session_basket
        GROUP BY user_id;
    """
    rows = run_query(db_params, query)
    return [float(r["avg_basket"]) for r in rows]


def fetch_purchase_prices(db_params):
    """Fetch purchase prices from database"""
    query = """
        SELECT price
        FROM customers
        WHERE event_type = 'purchase';
    """
    rows = run_query(db_params, query)
    return [float(r["price"]) for r in rows]


def print_stas(stats):
    """Print price stats"""
    print(f"count   {stats['count']:>15.6f}")
    print(f"mean    {stats['mean']:>15.6f}")
    print(f"std     {stats['std']:>15.6f}")
    print(f"min     {stats['min']:>15.6f}")
    print(f"25%     {stats['p25']:>15.6f}")
    print(f"50%     {stats['p50']:>15.6f}")
    print(f"75%     {stats['p75']:>15.6f}")
    print(f"max     {stats['max']:>15.6f}")


def plot_boxplot_full(prices, output_path):
    """Plot prices graph"""
    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.boxplot(prices, vert=False, widths=0.5)
    ax.set_xlabel("price")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def plot_boxplot_zoom(prices, output_path):
    """Plot prices zoom graph"""
    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.boxplot(prices, vert=False, widths=0.5)
    ax.set_xlabel("price")
    ax.set_xlim(-2, 13)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def plot_boxplot_basket(basket_values, output_path):
    """Plot average basket price graph"""
    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.boxplot(basket_values, vert=False, widths=0.5)
    ax.set_xlabel("average basket price per user")
    ax.set_xlim(0, 120)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def main():
    db_params = get_db_params()
    stats = fetch_price_stats(db_params)
    print_stas(stats)
    prices = fetch_purchase_prices(db_params)
    plot_boxplot_full(prices, "mustache_full.png")
    plot_boxplot_zoom(prices, "mustache_zoom.png")
    basket_values = fetch_avg_basket_per_user(db_params)
    plot_boxplot_basket(basket_values, "mustache_basket.png")


if __name__ == "__main__":
    main()
