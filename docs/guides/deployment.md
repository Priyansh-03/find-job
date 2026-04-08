# Deployment

## Production app entrypoint

- WSGI module: `app/wsgi.py`
- App object: `app`

## Gunicorn (recommended)

```bash
gunicorn app.wsgi:app -b 0.0.0.0:$PORT -w 1
```

## Render settings

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app.wsgi:app -b 0.0.0.0:$PORT -w 1`
- Root directory: leave blank (repo root)

## Alternative start command

`dashboard_app.py` supports `PORT` when present:

```bash
python dashboard_app.py
```

