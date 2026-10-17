# 21 - Nana's Blog : a real WordPress "Turtle Blog", recreated for the archive.
#
# Single self-contained container (WordPress 7.1.x + Apache/PHP 8.3 + MariaDB),
# all processes run as one unprivileged user `turtle` (uid 1000) so it works
# under the archive sandbox defaults (cap_drop: ALL, no-new-privileges) with no
# setuid/privilege-drop. Apache listens on :8888 to match the original and to
# avoid needing CAP_NET_BIND_SERVICE.
FROM wordpress:7.0.1-php8.3-apache

# --- packages: a local MariaDB + wp-cli + the bits wp-cli wants ---------------
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        mariadb-server mariadb-client less default-mysql-client ca-certificates; \
    rm -rf /var/lib/apt/lists/*; \
    curl -fsSL -o /usr/local/bin/wp \
        https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar; \
    chmod +x /usr/local/bin/wp

# --- unprivileged runtime user ------------------------------------------------
RUN set -eux; \
    useradd -m -u 1000 -s /bin/bash turtle

# --- Apache: listen on 8888, run as turtle, writable runtime dirs -------------
RUN set -eux; \
    sed -ri 's/^Listen .*/Listen 8888/' /etc/apache2/ports.conf; \
    sed -ri 's!<VirtualHost \*:80>!<VirtualHost *:8888>!' /etc/apache2/sites-available/000-default.conf; \
    echo 'ServerName localhost' >> /etc/apache2/apache2.conf; \
    # the original leaves xmlrpc.php enabled (that is part of the attack surface) \
    a2enmod rewrite >/dev/null; \
    # make everything Apache/WordPress/MariaDB touch owned by turtle \
    mkdir -p /run/mysqld /var/lib/mysql; \
    chown -R turtle:turtle /var/www/html /usr/src/wordpress /run/mysqld \
        /var/lib/mysql /var/log/apache2 /var/lib/apache2 /var/run/apache2 2>/dev/null || true; \
    chmod 1777 /tmp

# --- challenge files ----------------------------------------------------------
# /flag.txt lives on the container FS (not under the webroot, so it is never
# web-served) and is read only via post-exploitation RCE. World-readable, like
# the original's www-data-readable flag. Owned by turtle so a runtime $FLAG can
# overwrite it.
COPY flag.txt /flag.txt
COPY entrypoint.sh /usr/local/bin/ctf-entrypoint.sh
RUN chmod +x /usr/local/bin/ctf-entrypoint.sh; \
    chmod 644 /flag.txt; chown turtle:turtle /flag.txt

# siteurl/home default - the original's reverse-proxy fingerprint. Override at
# run time with -e WP_HOME=... if you want absolute links to use the real host.
ENV WP_HOME=http://localhost:8888 \
    WORDPRESS_DB_HOST=localhost:/run/mysqld/mysqld.sock \
    WORDPRESS_DB_USER=wordpress \
    WORDPRESS_DB_PASSWORD=wordpress \
    WORDPRESS_DB_NAME=wordpress

USER turtle
WORKDIR /var/www/html
EXPOSE 8888
ENTRYPOINT ["/usr/local/bin/ctf-entrypoint.sh"]
