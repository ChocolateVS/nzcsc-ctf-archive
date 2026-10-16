"""Standalone entrypoint for Challenge 3 "Traversal Troubles".

The whole-site aggregate does NOT import this file; it imports `traversal`
directly and registers `build_blueprint()` on its own shared app. This file is
only the single-challenge on-demand container's runner.
"""
from traversal import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
