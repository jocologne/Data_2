import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt


def get_params():
    """Database connection params"""
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


def referece_date(db_params):
    """Reference date for last purchase"""
    query = """
        SELECT MAX(event_time) AS max_date
        FROM customers
        WHERE event_type = 'purchase'
    """
    rows = run_query(db_params, query)
    return rows[0]["max_date"]


def rfs(db_params, reference_date):
    """Last purchase, frequency and spending"""
    query = """
        SELECT
            user_id,
            EXTRACT(DAY FROM (%s - MAX(event_time))) AS recency,
            COUNT(*) AS frequency,
            SUM(price) AS spending
        FROM customers
        WHERE event_type = 'purchase'
        GROUP BY user_id;
    """
    rows = run_query(db_params, query, (reference_date,))
    return rows


def build_feature_matrix(rfs_rows):
    """Build R,F,s matrix"""
    return [
        [float(r["recency"]), float(r["frequency"]), float(r["spending"])]
        for r in rfs_rows
    ]


def compute_inertias(features, k_range):
    """Compute distances from cluster center"""
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    inertias = []
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(features_scaled)
        inertias.append(kmeans.inertia_)
    return inertias


def plot_elbow(k_range, inertias, output_path):
    """Plot elbow line graph"""
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(list(k_range), inertias, marker="o")
    ax.set_title("The elbow method")
    ax.set_xlabel("Number of clusters")
    ax.set_ylabel("Inertia")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def main():
    """Generate elbow graph"""
    db_params = get_params()
    k_range = range(1, 11)
    referece = referece_date(db_params)
    rfs_rows = rfs(db_params, referece)
    features = build_feature_matrix(rfs_rows)
    inertias = compute_inertias(features, k_range)
    plot_elbow(k_range, inertias, "elbow.png")


if __name__ == "__main__":
    main()
