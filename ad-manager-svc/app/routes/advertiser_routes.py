from flask import Blueprint, jsonify, request

from app.routes.helpers import change_state, invalid_body_response, json_body, list_by_state
from app.services.advertiser_service import (
    create_advertiser,
    get_advertiser_by_id,
    get_advertiser_by_state,
    get_all_advertisers,
    update_advertiser,
    update_advertiser_state,
)

advertiser_blueprint = Blueprint('advertiser', __name__)


@advertiser_blueprint.route('/advertiser', methods=['POST'])
def create_advertiser_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    return jsonify({'message': 'Advertiser created successfully', 'advertiser': create_advertiser(json_data)}), 201


@advertiser_blueprint.route('/advertiser', methods=['PUT'])
def update_advertiser_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    updated_advertiser = update_advertiser(json_data)
    if updated_advertiser:
        return jsonify({'message': 'Advertiser updated successfully', 'advertiser': updated_advertiser}), 200
    return jsonify({'error': 'Advertiser not found'}), 404


@advertiser_blueprint.route('/advertiser/advertiserid/<advertiser_id>', methods=['GET'])
def get_advertiser_api(advertiser_id):
    advertiser = get_advertiser_by_id(advertiser_id)
    if advertiser:
        return jsonify(advertiser), 200
    return jsonify({'error': 'Advertiser not found'}), 404


@advertiser_blueprint.route('/advertiser', methods=['GET'])
def get_all_advertisers_api():
    return jsonify(get_all_advertisers()), 200


@advertiser_blueprint.route('/advertiser', methods=['PATCH'])
def update_advertiser_state_api():
    return change_state(update_advertiser_state, request.args.get('advertiser_id'), 'Advertiser')


@advertiser_blueprint.route('/advertiser/state/<state>', methods=['GET'])
def get_advertiser_by_state_api(state):
    return list_by_state(get_advertiser_by_state, state)
