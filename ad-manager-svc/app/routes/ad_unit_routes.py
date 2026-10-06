from flask import Blueprint, jsonify, request

from app.routes.helpers import change_state, invalid_body_response, json_body, list_by_state
from app.services.ad_unit_service import (
    create_ad_unit,
    get_ad_unit_by_id,
    get_ad_unit_by_publisher,
    get_ad_unit_by_state,
    get_all_ad_units,
    update_ad_unit,
    update_ad_unit_state,
)

ad_unit_blueprint = Blueprint('adunit', __name__)


@ad_unit_blueprint.route('/adunit', methods=['POST'])
def create_ad_unit_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    return jsonify({'message': 'Ad unit created successfully', 'ad_unit': create_ad_unit(json_data)}), 201


@ad_unit_blueprint.route('/adunit', methods=['PUT'])
def update_ad_unit_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    updated_ad_unit = update_ad_unit(json_data)
    if updated_ad_unit:
        return jsonify({'message': 'Ad unit updated successfully', 'ad_unit': updated_ad_unit}), 200
    return jsonify({'error': 'Ad unit not found'}), 404


@ad_unit_blueprint.route('/adunit/ad_unit_id/<ad_unit_id>', methods=['GET'])
def get_ad_unit_api(ad_unit_id):
    ad_unit = get_ad_unit_by_id(ad_unit_id)
    if ad_unit:
        return jsonify(ad_unit), 200
    return jsonify({'error': 'Ad unit not found'}), 404


@ad_unit_blueprint.route('/adunit', methods=['GET'])
def get_all_ad_units_api():
    return jsonify(get_all_ad_units()), 200


@ad_unit_blueprint.route('/adunit', methods=['PATCH'])
def update_ad_unit_state_api():
    return change_state(update_ad_unit_state, request.args.get('ad_unit_id'), 'Ad unit')


@ad_unit_blueprint.route('/adunit/state/<state>', methods=['GET'])
def get_ad_unit_by_state_api(state):
    return list_by_state(get_ad_unit_by_state, state)


@ad_unit_blueprint.route('/adunit/publisher/<publisher_id>', methods=['GET'])
def get_ad_unit_by_publisher_api(publisher_id):
    ad_units = get_ad_unit_by_publisher(publisher_id)
    if not ad_units:
        return jsonify({'error': 'Publisher not found'}), 404
    return jsonify(ad_units), 200
