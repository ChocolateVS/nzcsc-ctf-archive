#!/bin/bash
# Nana's Blog - bring up a local MariaDB, install + seed WordPress to look
# exactly like the original "Turtle Blog", then run Apache in the foreground.
# Everything runs as the unprivileged `turtle` user (no setuid / no caps).
set -euo pipefail

DATADIR=/var/lib/mysql
SOCK=/run/mysqld/mysqld.sock
WPROOT=/var/www/html
WP="wp --path=${WPROOT} --allow-root"

log() { echo "[ctf] $*"; }

# 1. WordPress core files into the webroot (first boot only) -------------------
if [ ! -e "${WPROOT}/wp-load.php" ]; then
    log "populating webroot with WordPress core"
    cp -a /usr/src/wordpress/. "${WPROOT}/"
fi

# 2. MariaDB: init datadir (first boot) then run with an --init-file ----------
# We run as the unprivileged `turtle` OS user, so root@localhost (unix_socket)
# is unusable and --bootstrap runs with --skip-grant-tables (CREATE USER/GRANT
# are refused there). mariadbd --init-file runs SQL at NORMAL startup, with the
# grant tables live, so account creation works. Idempotent (IF NOT EXISTS).
if [ ! -d "${DATADIR}/mysql" ]; then
    log "initialising MariaDB datadir"
    mariadb-install-db --datadir="${DATADIR}" --skip-test-db --auth-root-authentication-method=normal >/dev/null 2>&1
fi

cat > /tmp/init.sql <<SQL
CREATE DATABASE IF NOT EXISTS ${WORDPRESS_DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${WORDPRESS_DB_USER}'@'localhost' IDENTIFIED BY '${WORDPRESS_DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${WORDPRESS_DB_USER}'@'127.0.0.1' IDENTIFIED BY '${WORDPRESS_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${WORDPRESS_DB_NAME}.* TO '${WORDPRESS_DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON ${WORDPRESS_DB_NAME}.* TO '${WORDPRESS_DB_USER}'@'127.0.0.1';
SQL

log "starting MariaDB"
mariadbd --datadir="${DATADIR}" --socket="${SOCK}" \
    --pid-file=/run/mysqld/mysqld.pid --init-file=/tmp/init.sql \
    --bind-address=127.0.0.1 --port=3306 >/tmp/mariadb.log 2>&1 &

for i in $(seq 1 120); do
    if mariadb --socket="${SOCK}" -u"${WORDPRESS_DB_USER}" -p"${WORDPRESS_DB_PASSWORD}" \
         "${WORDPRESS_DB_NAME}" -e 'SELECT 1' >/dev/null 2>&1; then break; fi
    sleep 0.5
    [ "$i" = 120 ] && { log "MariaDB failed to start"; cat /tmp/mariadb.log; exit 1; }
done
log "MariaDB up"

# 4. wp-config + install (first boot only) -------------------------------------
if ! ${WP} core is-installed >/dev/null 2>&1; then
    log "configuring + installing WordPress"
    rm -f "${WPROOT}/wp-config.php"
    ${WP} config create \
        --dbname="${WORDPRESS_DB_NAME}" \
        --dbuser="${WORDPRESS_DB_USER}" \
        --dbpass="${WORDPRESS_DB_PASSWORD}" \
        --dbhost="${WORDPRESS_DB_HOST}" \
        --skip-check

    # Make home/siteurl track the host the site is actually served on, so the
    # blog works behind any proxy/domain (Caddy, localhost, ...) with no broken
    # redirects. (The live original hard-coded http://localhost:8888, which only
    # worked through its own reverse proxy.) Injected right after "<?php".
    awk 'NR==1{print; print "if (!empty($_SERVER[\"HTTP_HOST\"])) { $__p = ((!empty($_SERVER[\"HTTPS\"]) && $_SERVER[\"HTTPS\"] !== \"off\") || ((isset($_SERVER[\"HTTP_X_FORWARDED_PROTO\"]) ? $_SERVER[\"HTTP_X_FORWARDED_PROTO\"] : \"\") === \"https\")) ? \"https\" : \"http\"; define(\"WP_HOME\", $__p . \"://\" . $_SERVER[\"HTTP_HOST\"]); define(\"WP_SITEURL\", $__p . \"://\" . $_SERVER[\"HTTP_HOST\"]); }"; next} {print}' \
        "${WPROOT}/wp-config.php" > "${WPROOT}/wp-config.php.new" && mv "${WPROOT}/wp-config.php.new" "${WPROOT}/wp-config.php"

    ${WP} core install \
        --url="${WP_HOME}" \
        --title="Turtle Blog" \
        --admin_user="admin" \
        --admin_password="animalsrock" \
        --admin_email="admin@turle.local" \
        --skip-email

    log "seeding to match the original (empty Turtle Blog)"
    # strip ALL default content -> no posts, no pages, no comments (as scraped)
    ${WP} site empty --yes --uploads >/dev/null
    ${WP} option update blogname "Turtle Blog"
    ${WP} option update blogdescription ""
    ${WP} option update blog_public 0                   # "noindex,nofollow" robots meta, as the original
    ${WP} option update permalink_structure ""          # plain ?p= / ?rest_route= like the original
    ${WP} option update default_pingback_flag 0
    ${WP} option update default_ping_status closed
    ${WP} option update default_comment_status closed
    ${WP} option update users_can_register 0
    ${WP} option update timezone_string ""
    ${WP} option update gmt_offset 0
    ${WP} theme activate twentytwentyfive >/dev/null 2>&1 || true
    # no plugins active, matching the default install
    ${WP} plugin deactivate --all >/dev/null 2>&1 || true
    # lose the shipped readme/licence so version/dir probes match a tidy box
    rm -f "${WPROOT}/readme.html" "${WPROOT}/license.txt" "${WPROOT}/wp-config-docker.php"
fi

# home/siteurl are resolved dynamically from HTTP_HOST in wp-config.php (above),
# so the DB values are just the CLI fallback; no per-boot override needed.

# 5. refresh the flag from $FLAG if the deploy injected one --------------------
if [ -n "${FLAG:-}" ] && [ -w /flag.txt ]; then
    printf '%s\n' "${FLAG}" > /flag.txt
fi
log "flag in place at /flag.txt"

# 6. serve -------------------------------------------------------------------
log "starting Apache on :8888"
export APACHE_RUN_USER=turtle APACHE_RUN_GROUP=turtle
export APACHE_PID_FILE=/tmp/apache2.pid
export APACHE_RUN_DIR=/tmp/apache2-run APACHE_LOCK_DIR=/tmp/apache2-lock APACHE_LOG_DIR=/var/log/apache2
mkdir -p "$APACHE_RUN_DIR" "$APACHE_LOCK_DIR"
exec apache2 -D FOREGROUND
