# SecureDesk Tracker

Secure incident desk and file management system built with Django.

## Features
- Secure user authentication with Django and two-factor support
- File upload and vault management with Cloudinary raw storage
- Incident and help ticket workflow with SLA tracking and escalation
- Knowledge base search, audit logging, and admin dashboard analytics
- JWT API endpoint for incident ticket creation

## Setup
1. Create and activate the virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Apply database migrations

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

4. Create a superuser

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

5. Start the development server

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

6. Open in browser

```text
http://127.0.0.1:8000/
```
## Deploying to Render
This project is ready for Render deployment and includes `Procfile` and `runtime.txt`.

### Recommended Render setup
1. Create a new **Web Service** on Render.
2. Connect your Git repository containing this project.
3. Use the default Python environment.
4. Set the start command to:

```bash
gunicorn config.wsgi:application
```

5. Set the build command to:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

6. Add these environment variables in Render:
   - `DEBUG=False`
   - `SECRET_KEY` (set to a strong secret)
   - `ALLOWED_HOSTS=your-app.onrender.com`
   - `CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com`
   - `DATABASE_URL` (recommended PostgreSQL for Render)
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_SMS_RECIPIENTS` if using SMS alerts
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` if using Cloudinary file storage

### Important Render note
Render's filesystem is ephemeral, so SQLite is not recommended for production. Use PostgreSQL with `DATABASE_URL` instead.

Once deployed, Render will provide a live URL you can share for your final defense.

### Post-deploy: running migrations on Render
Render does not automatically run Django migrations unless configured. To ensure the database schema is updated (this project added new incident fields and attachments), set a **Release Command** in your Render service settings to run migrations and collect static files during each deploy. Example release command:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

If you prefer to run migrations manually after a deploy, open the Render web shell for your service and run:

```bash
python manage.py migrate
```

Notes:
- The pushed commits include new migration files under `filemanager/migrations/0008_*.py` and `0009_incidentattachment.py` which must be applied on the production database.
- Ensure `DATABASE_URL` points to a writable PostgreSQL instance before running migrations.
- If you encounter issues, check Render logs for `manage.py migrate` output and database connectivity errors.

## Notes
- 2FA support is enabled through `django-two-factor-auth`
- Email notifications currently use the console backend
- Configure `TWILIO_*` environment variables for SMS alert delivery
- Keep `DEBUG=False` in production and use a proper WSGI/ASGI host
