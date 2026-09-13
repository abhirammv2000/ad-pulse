import os

from flask import Flask, jsonify
from flask_cors import CORS

from config import Config


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # CORS is configured here rather than in run.py so it also applies under
    # gunicorn, which imports `app` and never executes run.py's main block.
    CORS(app, origins=os.getenv("CORS_ALLOWED_ORIGINS", "*").split(","))

    register_blueprints(app)

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok'}), 200

    return app


def register_blueprints(app):
    from app.cache import cache_blueprint
    from app.routes.ad_routes import ad_blueprint
    from app.routes.ad_unit_routes import ad_unit_blueprint
    from app.routes.advertiser_routes import advertiser_blueprint
    from app.routes.campaign_routes import campaign_blueprint
    from app.routes.creative_routes import creative_blueprint
    from app.routes.publisher_routes import publisher_blueprint
    from app.routes.reporting_routes import reporting_blueprint

    for blueprint in (
        cache_blueprint,
        ad_blueprint,
        ad_unit_blueprint,
        advertiser_blueprint,
        campaign_blueprint,
        creative_blueprint,
        publisher_blueprint,
        reporting_blueprint,
    ):
        app.register_blueprint(blueprint)
