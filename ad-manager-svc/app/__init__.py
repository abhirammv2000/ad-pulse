from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.cache import cache_blueprint
    app.register_blueprint(cache_blueprint)

    from app.routes.publisher_routes import publisher_blueprint
    app.register_blueprint(publisher_blueprint)

    return app
