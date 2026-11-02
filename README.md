# Hands Together — Community Support Platform

A responsive website for a Bangladesh community support platform. It includes a home page, account registration and sign-in, a Lost & Found board, and a volunteer opportunities page. Flask handles page routes and JSON APIs; SQLite stores submitted data locally.

## Run it with Flask

Install Python 3 first if it is not already on your computer: https://www.python.org/downloads/windows/. On Windows, the installer should make the `py` command available. Then install the Flask dependency from a terminal in this folder:

```bash
py -m pip install -r requirements.txt
```

Start the Flask development server:

```bash
py app.py
```

Then visit `http://127.0.0.1:5000`. The Flask app provides `/`, `/signup`, `/login`, `/found`, and `/volunteer` routes. Port 5000 avoids conflicting with the earlier static preview server on port 8000.

On Windows, you can instead double-click `run.bat`. It installs the listed Flask dependency and starts the app.

## Pages

- `index.html` — home and navigation
- `signup.html` — sign-up form
- `login.html` — log-in form
- `found.html` — searchable Lost & Found reports, report form, and safety messaging
- `volunteer.html` — searchable activity board and join form
- `app.py` — Flask application and page routes
- `run.bat` — Windows setup and launch helper
- `requirements.txt` — Python dependency list
- `hands_together.db` — created automatically on first run; contains local users, reports, and volunteer sign-ups
- `styles.css` and `app.js` — shared layout and browser behavior

## Prototype scope

Flask serves the pages and API. SQLite creates `hands_together.db` beside `app.py` on the first run. Account passwords are stored as salted hashes. Lost and found reports and volunteer interest forms are stored in that local database. Missing-person reports are saved with `pending_review` status and do not appear in public results. Sample listings and dates in the browser are demonstration content. Google Fonts are optional; the site falls back to system fonts if they are unavailable. This is a local project prototype; use a production WSGI server, deployment secret, and reviewed privacy/moderation workflow before putting it on the public internet.
