from flask import Blueprint, jsonify, request

from app.routes.helpers import change_state, invalid_body_response, json_body, list_by_state
from app.services.ad_service import (
    create_ad,
    get_ad_by_campaign_and_advertiser_id,
    get_ad_by_id,
    get_ad_by_state,
    get_all_ads,
    update_ad,
    update_ad_state,
)

ad_blueprint = Blueprint('ad', __name__)


@ad_blueprint.route('/ad', methods=['GET'])
def get_all_ads_api():
    return jsonify(get_all_ads()), 200


@ad_blueprint.route('/ad', methods=['POST'])
def create_ad_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    return jsonify({'message': 'Ad created successfully', 'ad': create_ad(json_data)}), 201


@ad_blueprint.route('/ad/adid/<ad_id>', methods=['GET'])
def get_ad_by_id_api(ad_id):
    ad = get_ad_by_id(ad_id)
    if ad:
        return jsonify(ad), 200
    return jsonify({'error': 'Ad not found'}), 404


@ad_blueprint.route('/ad/state/<state>', methods=['GET'])
def get_ad_by_state_api(state):
    return list_by_state(get_ad_by_state, state)


@ad_blueprint.route('/ad', methods=['PATCH'])
def update_ad_state_api():
    return change_state(update_ad_state, request.args.get('ad_id'), 'Ad')


@ad_blueprint.route('/ad', methods=['PUT'])
def update_ad_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    updated_ad = update_ad(json_data)
    if updated_ad:
        return jsonify({'message': 'Ad updated successfully', 'ad': updated_ad}), 200
    return jsonify({'error': 'Ad not found'}), 404


@ad_blueprint.route('/ad/advertiser/<advertiser_id>/campaign/<campaign_id>', methods=['GET'])
def get_ad_by_campaign_and_advertiser_api(advertiser_id, campaign_id):
    return jsonify(get_ad_by_campaign_and_advertiser_id(advertiser_id, campaign_id)), 200
