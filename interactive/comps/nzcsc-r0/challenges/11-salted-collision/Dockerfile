# Salted Collision - PHP "magic hash" / type-juggling challenge.
# Faithful to the original, which served over Apache/2.4.x (Debian) + PHP.
# The FLAG is injected at runtime via the FLAG env var (from flags.env); it never
# lives in the image or in git. SECRET_PASSWORD is fixed in config.php so the
# intended solve path reproduces exactly.
FROM php:8.2-apache

# Leaked source is intentional (highlight_file); the real secrets live in
# config.php which PHP executes rather than serving as text.
COPY index.php /var/www/html/index.php
COPY config.php /var/www/html/config.php

# Apache serves on 80 in this base image.
EXPOSE 80
