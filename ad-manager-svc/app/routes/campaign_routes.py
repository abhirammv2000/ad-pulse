from flask import Blueprint, jsonify, request

from app.routes.helpers import change_state, invalid_body_response, json_body, list_by_state
from app.services.campaign_service import (
    create_campaign,
    get_all_campaigns,
    get_campaign_by_advertiser_id,
    get_campaign_by_id,
    get_campaign_by_state,
    update_campaign,
    update_campaign_state,
)

campaign_blueprint = Blueprint('campaign', __name__)


@campaign_blueprint.route('/campaign', methods=['GET'])
def get_all_campaigns_api():
    return jsonify(get_all_campaigns()), 200


@campaign_blueprint.route('/campaign/<campaignid>', methods=['GET'])
def get_campaign_by_id_api(campaignid):
    campaign = get_campaign_by_id(campaignid)
    if campaign is None:
        return jsonify({'error': 'Campaign not found'}), 404
    return jsonify(campaign), 200


@campaign_blueprint.route('/campaign/state/<state>', methods=['GET'])
def get_campaign_by_state_api(state):
    return list_by_state(get_campaign_by_state, state)


@campaign_blueprint.route('/campaign', methods=['POST'])
def create_campaign_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    return jsonify({'message': 'Campaign created', 'campaign': create_campaign(json_data)}), 201


@campaign_blueprint.route('/campaign', methods=['PUT'])
def update_campaign_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    updated_campaign = update_campaign(json_data)
    if updated_campaign is None:
        return jsonify({'error': 'Campaign not found'}), 404
    return jsonify({'message': 'Campaign updated', 'campaign': updated_campaign}), 200


@campaign_blueprint.route('/campaign', methods=['PATCH'])
def update_campaign_state_api():
    return change_state(update_campaign_state, request.args.get('campaign_id'), 'Campaign')


@campaign_blueprint.route('/campaign/advertiser/<advertiser_id>', methods=['GET'])
def get_campaign_by_advertiser_api(advertiser_id):
    return jsonify(get_campaign_by_advertiser_id(advertiser_id)), 200
