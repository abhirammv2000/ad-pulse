import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Development entrypoint only. The container runs gunicorn against the
    # `app` object above; debug mode here would expose the Werkzeug console.
    app.run(
        debug=os.getenv("FLASK_DEBUG", "").lower() in ("1", "true"),
        host='0.0.0.0',
        port=int(os.getenv("PORT", "5000")),
    )
