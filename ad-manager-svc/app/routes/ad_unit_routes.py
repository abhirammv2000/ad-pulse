from flask import request, jsonify, Blueprint
from app.enums.States import States
from app.services.ad_unit_service import create_ad_unit, update_ad_unit, get_ad_unit_by_id, get_all_ad_units, update_ad_unit_state, get_ad_unit_by_state, get_ad_unit_by_publisher

ad_unit_blueprint = Blueprint('adunit', __name__)

@ad_unit_blueprint.route('/adunit', methods=['POST'])
def create_ad_unit_api():
    # Parse JSON data from request
    json_data = request.json
    
    # Call the function to create a new ad unit
    created_ad_unit = create_ad_unit(json_data)
    
    return jsonify({'message': 'Ad unit created successfully', 
                    'ad_unit': created_ad_unit
                    }), 201


@ad_unit_blueprint.route('/adunit', methods=['PUT'])
def update_ad_unit_api():
    # Parse JSON data from request
    json_data = request.json
    
    # Update the ad unit
    updated_ad_unit = update_ad_unit(json_data)
    
    if updated_ad_unit:
        return jsonify({
            'message': 'Ad unit updated successfully',
            'ad_unit': updated_ad_unit
        }), 200
    else:
        return jsonify({'error': 'Ad unit not found'}), 404

@ad_unit_blueprint.route('/adunit/ad_unit_id/<ad_unit_id>', methods=['GET']) 
def get_ad_unit_api(ad_unit_id):
    # Get the ad unit
    ad_unit = get_ad_unit_by_id(ad_unit_id)
    
    if ad_unit:
        return ad_unit, 200
    else:
        return jsonify({'error': 'Ad unit not found'}), 404
    
@ad_unit_blueprint.route('/adunit', methods=['GET'])
def get_all_ad_units_api():
    # Get all ad units
    ad_units = get_all_ad_units()
    
    return ad_units, 200

@ad_unit_blueprint.route('/adunit', methods=['PATCH'])
def update_ad_unit_state_api():
    ad_unit_id = request.args.get('ad_unit_id')
    new_state = request.args.get('state')
    if new_state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    if new_state == States.CREATED.value:
        return jsonify({'error': 'Invalid State Transition'}), 400
    if update_ad_unit_state(ad_unit_id, new_state):
        return jsonify({'message': f'Ad unit state updated successfully to {new_state}'}), 200
    else:
        return jsonify({'error': 'Ad unit not found'}), 404
    
@ad_unit_blueprint.route('/adunit/state/<state>', methods=['GET'])
def get_ad_unit_by_state_api(state):
    if state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    ad_units = get_ad_unit_by_state(state)
    return ad_units, 200

@ad_unit_blueprint.route('/adunit/publisher/<publisher_id>', methods=['GET'])
def get_ad_unit_by_publisher_api(publisher_id):
    if not publisher_id:
        return jsonify({'error': 'Publisher ID not provided'}), 400
    ad_units = get_ad_unit_by_publisher(publisher_id)
    if not ad_units:
        return jsonify({'error': 'Publisher not found'}), 404
    return ad_units, 200
