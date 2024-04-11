from flask import request, jsonify, Blueprint
from app.enums.States import States
from app.services.advertiser_service import create_advertiser, update_advertiser, get_advertiser_by_id, get_all_advertisers, update_advertiser_state, get_advertiser_by_state

advertiser_blueprint = Blueprint('advertiser', __name__)

@advertiser_blueprint.route('/advertiser', methods=['POST'])
def create_advertiser_api():
    # Parse JSON data from request
    json_data = request.json
    
    # Call the function to create a new advertiser
    created_advertiser = create_advertiser(json_data)
    
    return jsonify({'message': 'Advertiser created successfully', 
                    'advertiser': created_advertiser
                    }), 201


@advertiser_blueprint.route('/advertiser', methods=['PUT'])
def update_advertiser_api():
    # Parse JSON data from request
    json_data = request.json
    
    # Update the advertiser
    updated_advertiser = update_advertiser(json_data)
    
    if updated_advertiser:
        return jsonify({
            'message': 'Advertiser updated successfully',
            'advertiser': updated_advertiser
        }), 200
    else:
        return jsonify({'error': 'Advertiser not found'}), 404
    

@advertiser_blueprint.route('/advertiser/advertiserid/<advertiser_id>', methods=['GET'])
def get_advertiser_api(advertiser_id):
    # Get the advertiser
    advertiser = get_advertiser_by_id(advertiser_id)
    
    if advertiser:
        return advertiser, 200
    else:
        return jsonify({'error': 'Advertiser not found'}), 404
    

    
@advertiser_blueprint.route('/advertiser', methods=['GET'])
def get_all_advertisers_api():
    # Get all advertisers
    advertisers = get_all_advertisers()
    
    return advertisers, 200



@advertiser_blueprint.route('/advertiser', methods=['PATCH'])
def update_advertiser_state_api():
    advertiser_id = request.args.get('advertiser_id')
    new_state = request.args.get('new_state')
    if new_state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    if new_state == States.CREATED.value:
        return jsonify({'error': 'Invalid State Transition'}), 400
    if update_advertiser_state(advertiser_id, new_state):
        return jsonify({'message': 'Advertiser state updated successfully to {new_state}'}), 200
    else:
        return jsonify({'error': 'Advertiser not found'}), 404
    


@advertiser_blueprint.route('/advertiser/state/<state>', methods=['GET'])
def get_advertiser_by_state_api(state):
    if state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    advertisers = get_advertiser_by_state(state)
    return advertisers, 200
