import json
import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from config import Config
from config.db import init_db

log = logging.getLogger(__name__)


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # CORS is set up here and not in run.py so it also applies under gunicorn,
    # which imports `app` and never runs run.py's main block.
    CORS(app, origins=os.getenv("CORS_ALLOWED_ORIGINS", "*").split(","))

    register_blueprints(app)
    register_error_handlers(app)

    # There is no migration tool, so this is what creates the Postgres schema.
    # It only adds tables that are missing, so it is safe to run on every start.
    init_db()

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


def register_error_handlers(app):
    """Return JSON for every error, so API clients never get an HTML page."""

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        # A required column was empty, or an id points at a row that doesn't exist.
        log.warning("rejected request: %s", error.orig)
        return jsonify({'error': 'Missing required field or unknown reference id'}), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        # Keep the response Flask built (it carries headers such as Allow on a
        # 405) and swap in a JSON body.
        response = error.get_response()
        response.data = json.dumps({'error': error.description})
        response.content_type = 'application/json'
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        log.exception("unhandled error")
        return jsonify({'error': 'Internal server error'}), 500
