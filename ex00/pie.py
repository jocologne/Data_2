import psycopg2
import matplotlib.pyplot as plt


def get_db_params():
    """Keep params of database to be read"""
    return {
        "host": "localhost",
        "port": "5432",
        "dbname": "piscineds",
        "user": "jcologne",
        "password": "mysecretpassword",
    }


def fetch_event_counts(db_params):
    """Counts events in database"""
    query = """
        SELECT event_type, COUNT(*) AS total
        FROM customers
        GROUP BY event_type
        ORDER BY total DESC
    """
    conn = psycopg2.connect(**db_params)
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows


def plot_pie(rows, output_path):
    """Plot pie char for data received"""
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=0)
    fig.tight_layout()
    fig.savefig(output_path)


def main():
    """Read Database and plot pie chart for events"""
    db_params = get_db_params()
    rows = fetch_event_counts(db_params)
    plot_pie(rows, output_path="pie.png")


if __name__ == "__main__":
    main()
