from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.cache import cache_blueprint
    app.register_blueprint(cache_blueprint)

    from app.routes.publisher_routes import publisher_blueprint
    app.register_blueprint(publisher_blueprint)

    from app.routes.ad_routes import ad_blueprint
    app.register_blueprint(ad_blueprint)

    from app.routes.advertiser_routes import advertiser_blueprint
    app.register_blueprint(advertiser_blueprint)

    from app.routes.ad_unit_routes import ad_unit_blueprint 
    app.register_blueprint(ad_unit_blueprint)

    from app.routes.creative_routes import creative_blueprint
    app.register_blueprint(creative_blueprint)

    from app.routes.campaign_routes import campaign_blueprint
    app.register_blueprint(campaign_blueprint)

    from app.routes.reporting_routes import reporting_blueprint
    app.register_blueprint(reporting_blueprint)

    return app
