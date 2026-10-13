import json
import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy.exc import DataError, IntegrityError
from werkzeug.exceptions import HTTPException

from app.auth import install_api_key_auth
from config import Config
from config.db import init_db

log = logging.getLogger(__name__)


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # CORS is set up here and not in run.py so it also applies under gunicorn,
    # which imports `app` and never runs run.py's main block.
    CORS(app, origins=os.getenv("CORS_ALLOWED_ORIGINS", "*").split(","))

    install_api_key_auth(app)

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


def _violated_column(error):
    """The column Postgres names in a not-null violation, or None. A foreign key violation names a constraint instead."""
    diag = getattr(error.orig, 'diag', None)
    return getattr(diag, 'column_name', None) or None


def register_error_handlers(app):
    """Return JSON for every error, so API clients never get an HTML page."""

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        # A required column was empty, or an id points at a row that doesn't exist.
        log.warning("rejected request: %s", error.orig)
        body = {'error': 'Missing required field or unknown reference id'}
        field = _violated_column(error)
        if field:
            body['field'] = field
        return jsonify(body), 400

    @app.errorhandler(DataError)
    def handle_data_error(error):
        # The database could not read a value: "next week" for a date, "abc" for a number. The client sent bad
        # data, so this is a 400, not a 500. The database's own message is logged and not returned, because it
        # quotes the value and names internals.
        #
        # The database is left to decide what is a valid value, on purpose. Postgres accepts more date formats
        # than ISO 8601 and the dashboard sends numbers such as the ad priority as strings, so a stricter check
        # written here would reject requests that work today.
        log.warning("rejected request: %s", error.orig)
        return jsonify({'error': 'A value is in the wrong format for its field, for example a date or a number'}), 400

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
