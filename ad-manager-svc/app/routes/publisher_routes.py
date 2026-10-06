from flask import Blueprint, jsonify, request

from app.routes.helpers import change_state, invalid_body_response, json_body, list_by_state
from app.services.publisher_service import (
    create_publisher,
    get_all_publishers,
    get_publisher_by_id,
    get_publisher_by_state,
    update_publisher,
    update_publisher_state,
)

publisher_blueprint = Blueprint('publisher', __name__)


@publisher_blueprint.route('/publisher', methods=['POST'])
def create_publisher_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    return jsonify({'message': 'Publisher created successfully', 'publisher': create_publisher(json_data)}), 201


@publisher_blueprint.route('/publisher', methods=['PUT'])
def update_publisher_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    updated_publisher = update_publisher(json_data)
    if updated_publisher:
        return jsonify({'message': 'Publisher updated successfully', 'publisher': updated_publisher}), 200
    return jsonify({'error': 'Publisher not found'}), 404


@publisher_blueprint.route('/publisher/publisherid/<publisher_id>', methods=['GET'])
def get_publisher_api(publisher_id):
    publisher = get_publisher_by_id(publisher_id)
    if publisher:
        return jsonify(publisher), 200
    return jsonify({'error': 'Publisher not found'}), 404


@publisher_blueprint.route('/publisher', methods=['GET'])
def get_all_publishers_api():
    return jsonify(get_all_publishers()), 200


@publisher_blueprint.route('/publisher', methods=['PATCH'])
def update_publisher_state_api():
    return change_state(update_publisher_state, request.args.get('publisher_id'), 'Publisher')


@publisher_blueprint.route('/publisher/state/<state>', methods=['GET'])
def get_publisher_by_state_api(state):
    return list_by_state(get_publisher_by_state, state)
