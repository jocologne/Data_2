#!/bin/bash
#
# setup.sh - Modulo 2 (Data Viz)
#
# Pipeline completo, do zero ate o Data Warehouse pronto para os graficos:
#   1. Baixa subject.zip (customer/ + items/) e o data_2023_feb.csv extra
#   2. Organiza a estrutura de pastas na raiz do projeto
#   3. Sobe PostgreSQL + pgAdmin via Docker Compose (gerado dinamicamente)
#   4. Cria e popula as tabelas data_202*_*** (incluindo fevereiro) e items
#   5. Cria a tabela 'customers' unindo todas as tabelas mensais (dinamico)
#   6. Remove duplicatas (exatas e com <= 1s de diferenca)
#   7. Faz o fusion (LEFT JOIN) de customers com items, sem perder dados
#
# Resultado final: tabela 'customers' pronta para os exercicios do Modulo 2.
#
# Uso: ./setup.sh   (executar a partir da raiz do projeto do Modulo 2)

set -e

# ------------------------------------------------------------------
# Configuracao
# ------------------------------------------------------------------
DB_USER="jcologne"
DB_PASSWORD="mysecretpassword"
DB_NAME="piscineds"
DB_HOST="localhost"
DB_PORT="5432"

PGADMIN_EMAIL="jcologne@student.42sp.org.br"
PGADMIN_PASSWORD="mysecretpassword"
PGADMIN_PORT="5050"

SUBJECT_URL="https://cdn.intra.42.fr/document/document/50816/subject.zip"
FEB_CSV_URL="https://cdn.intra.42.fr/document/document/50814/data_2023_feb.csv"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$SCRIPT_DIR"

DOWNLOAD_DIR="$WORKDIR/.setup_tmp"
ZIP_FILE="$DOWNLOAD_DIR/subject.zip"
EXTRACT_DIR="$DOWNLOAD_DIR/extracted"
COMPOSE_FILE="$WORKDIR/docker-compose.yml"

export PGPASSWORD="$DB_PASSWORD"
PSQL="psql -U $DB_USER -d $DB_NAME -h $DB_HOST -p $DB_PORT --pset=pager=off"

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
log() { echo -e "\n\033[1;34m==>\033[0m $1"; }
error_exit() { echo -e "\033[1;31mERRO:\033[0m $1" >&2; exit 1; }
check_command() { command -v "$1" >/dev/null 2>&1 || error_exit "'$1' nao encontrado."; }

# ------------------------------------------------------------------
# 0. Dependencias
# ------------------------------------------------------------------
log "Checando dependencias..."
check_command curl
check_command unzip
check_command docker
check_command psql
docker compose version >/dev/null 2>&1 || error_exit "'docker compose' (plugin v2) nao encontrado."

# ------------------------------------------------------------------
# 1. Baixar subject.zip (customer/ + items/)
# ------------------------------------------------------------------
log "Baixando subject.zip..."
mkdir -p "$DOWNLOAD_DIR"

if [ -f "$ZIP_FILE" ]; then
    echo "Ja existe em $ZIP_FILE, pulando download."
else
    curl -fSL "$SUBJECT_URL" -o "$ZIP_FILE" || error_exit "Falha ao baixar $SUBJECT_URL"
fi

log "Extraindo e localizando pastas customer/items..."
mkdir -p "$EXTRACT_DIR"
unzip -oq "$ZIP_FILE" -d "$EXTRACT_DIR"

CUSTOMER_SRC=$(find "$EXTRACT_DIR" -type d -iname "customer" | head -n 1)
ITEMS_SRC=$(find "$EXTRACT_DIR" -type d \( -iname "items" -o -iname "item" \) | head -n 1)

[ -n "$CUSTOMER_SRC" ] || error_exit "Pasta 'customer' nao encontrada no zip."
[ -n "$ITEMS_SRC" ] || error_exit "Pasta 'items'/'item' nao encontrada no zip."

if [ -d "$WORKDIR/customer" ]; then
    echo "customer/ ja existe na raiz, mantendo."
else
    mv "$CUSTOMER_SRC" "$WORKDIR/customer"
    echo "-> customer/ movida para a raiz."
fi

if [ -d "$WORKDIR/items" ]; then
    echo "items/ ja existe na raiz, mantendo."
else
    mv "$ITEMS_SRC" "$WORKDIR/items"
    echo "-> items/ movida para a raiz."
fi

rm -rf "$DOWNLOAD_DIR"

# ------------------------------------------------------------------
# 2. Baixar o CSV extra de fevereiro (entra dentro de customer/)
# ------------------------------------------------------------------
log "Baixando data_2023_feb.csv..."
FEB_CSV_PATH="$WORKDIR/customer/data_2023_feb.csv"

if [ -f "$FEB_CSV_PATH" ]; then
    echo "Ja existe em $FEB_CSV_PATH, pulando download."
else
    curl -fSL "$FEB_CSV_URL" -o "$FEB_CSV_PATH" || error_exit "Falha ao baixar $FEB_CSV_URL"
    echo "-> data_2023_feb.csv adicionado a customer/"
fi

# ------------------------------------------------------------------
# 3. Subir Postgres + pgAdmin a partir do docker-compose.yml da raiz
# ------------------------------------------------------------------
log "Subindo Postgres + pgAdmin via $COMPOSE_FILE ..."

[ -f "$COMPOSE_FILE" ] || error_exit "docker-compose.yml nao encontrado em $WORKDIR. Coloque-o na raiz do projeto, junto do setup.sh."

docker rm -f piscineds_postgres piscineds_pgadmin >/dev/null 2>&1 || true
docker compose -f "$COMPOSE_FILE" up -d

log "Aguardando Postgres ficar saudavel..."
ATTEMPTS=0
until docker exec piscineds_postgres pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
    ATTEMPTS=$((ATTEMPTS + 1))
    [ "$ATTEMPTS" -ge 30 ] && error_exit "Postgres nao ficou pronto a tempo."
    sleep 2
done
echo "Postgres pronto."

# ------------------------------------------------------------------
# 4. Criar e popular tabelas data_202*_*** (inclui fevereiro automaticamente)
# ------------------------------------------------------------------
log "Criando e populando tabelas data_202*_*** a partir de customer/ ..."

CUSTOMER_SQL="/tmp/setup_customer_tables.sql"
> "$CUSTOMER_SQL"

shopt -s nullglob
csv_files=("$WORKDIR"/customer/*.csv)
[ ${#csv_files[@]} -eq 0 ] && error_exit "Nenhum CSV encontrado em $WORKDIR/customer/"

for csv in "${csv_files[@]}"; do
    table_name=$(basename "$csv" .csv)
    csv_abs=$(realpath "$csv")
    cat >> "$CUSTOMER_SQL" <<EOF
DROP TABLE IF EXISTS $table_name;
CREATE TABLE $table_name (
    event_time     TIMESTAMP,
    event_type     VARCHAR(20),
    product_id     INTEGER,
    price          NUMERIC(10,2),
    user_id        BIGINT,
    user_session   UUID
);
\copy $table_name FROM '$csv_abs' DELIMITER ',' CSV HEADER;
EOF
    echo "-> tabela '$table_name' preparada."
done

$PSQL -f "$CUSTOMER_SQL"

# ------------------------------------------------------------------
# 5. Criar e popular a tabela items
# ------------------------------------------------------------------
log "Criando e populando a tabela 'items'..."

ITEMS_CSV=$(find "$WORKDIR/items" -maxdepth 1 -iname "*.csv" | head -n 1)
[ -n "$ITEMS_CSV" ] || error_exit "Nenhum CSV encontrado em $WORKDIR/items/"
ITEMS_CSV_ABS=$(realpath "$ITEMS_CSV")

$PSQL -c "
DROP TABLE IF EXISTS items;
CREATE TABLE items (
    product_id      INTEGER,
    category_id     BIGINT,
    category_code   VARCHAR(100),
    brand           VARCHAR(50)
);
"

ITEMS_SQL="/tmp/setup_items_table.sql"
cat > "$ITEMS_SQL" <<EOF
\copy items FROM '$ITEMS_CSV_ABS' DELIMITER ',' CSV HEADER;
EOF

$PSQL -f "$ITEMS_SQL"

# ------------------------------------------------------------------
# 6. Criar 'customers' unindo dinamicamente as tabelas mensais
# ------------------------------------------------------------------
log "Unindo tabelas mensais em 'customers' (UNION ALL dinamico)..."

TABLES=$($PSQL -t -A -c "
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name ~ '^data_202[0-9]_[a-z]+\$'
    ORDER BY table_name;
")

[ -z "$TABLES" ] && error_exit "Nenhuma tabela data_202*_*** encontrada."
echo "Tabelas incluidas na uniao:"
echo "$TABLES" | sed 's/^/  - /'

UNION_QUERY=""
first=true
while read -r table; do
    [ -z "$table" ] && continue
    if [ "$first" = true ]; then
        UNION_QUERY="SELECT * FROM $table"
        first=false
    else
        UNION_QUERY="$UNION_QUERY UNION ALL SELECT * FROM $table"
    fi
done <<< "$TABLES"

$PSQL -c "
DROP TABLE IF EXISTS customers;
CREATE TABLE customers AS
$UNION_QUERY;
"

# ------------------------------------------------------------------
# 7. Remover duplicatas (exatas e com <= 1s de diferenca)
# ------------------------------------------------------------------
log "Removendo duplicatas de 'customers'..."

$PSQL -c "
DROP TABLE IF EXISTS customers_clean;
CREATE TABLE customers_clean AS
SELECT event_time, event_type, product_id, price, user_id, user_session
FROM (
    SELECT *,
        event_time - LAG(event_time) OVER (
            PARTITION BY event_type, product_id, price, user_id, user_session
            ORDER BY event_time
        ) AS time_diff
    FROM customers
) sub
WHERE time_diff IS NULL OR time_diff > INTERVAL '1 second';

DROP TABLE customers;
ALTER TABLE customers_clean RENAME TO customers;
"

# ------------------------------------------------------------------
# 8. Fusion com items (LEFT JOIN, sem perder dados)
# ------------------------------------------------------------------
log "Fazendo fusion de 'customers' com 'items'..."

$PSQL -c "
DROP TABLE IF EXISTS items_dedup;
CREATE TABLE items_dedup AS
SELECT DISTINCT ON (product_id)
    product_id, category_id, category_code, brand
FROM items
ORDER BY product_id, (category_code IS NULL), (brand IS NULL);

DROP TABLE IF EXISTS customers_fusion;
CREATE TABLE customers_fusion AS
SELECT
    c.event_time, c.event_type, c.product_id, c.price,
    c.user_id, c.user_session,
    i.category_id, i.category_code, i.brand
FROM customers c
LEFT JOIN items_dedup i ON c.product_id = i.product_id;

DROP TABLE customers;
DROP TABLE items_dedup;
ALTER TABLE customers_fusion RENAME TO customers;
"

# ------------------------------------------------------------------
# 9. Resumo final
# ------------------------------------------------------------------
log "Resumo final:"
$PSQL -c "SELECT COUNT(*) AS total_customers FROM customers;"
$PSQL -c "\dt"

log "Setup do Modulo 2 concluido! Data Warehouse pronto para os graficos."
echo ""
echo "Postgres  -> psql -U $DB_USER -d $DB_NAME -h $DB_HOST -W"
echo "pgAdmin   -> http://127.0.0.1:$PGADMIN_PORT  (login: $PGADMIN_EMAIL / $PGADMIN_PASSWORD)"