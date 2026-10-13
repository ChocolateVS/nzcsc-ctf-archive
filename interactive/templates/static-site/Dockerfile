# Static-site challenge (plain HTML/JS, e.g. client-side puzzles). Put the site under
# site/. nginx serves it on port 80 (matches `port: 80` in challenge.yml).
# If the flag needs to be embedded in the page, template it in at build time instead of
# committing it: pass it as a build arg from the generator, or bake it in a start script.
FROM nginx:alpine
COPY site/ /usr/share/nginx/html/
EXPOSE 80
