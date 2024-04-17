from flask import request, jsonify, Blueprint
from app.enums.States import States
from app.services.publisher_service import create_publisher, update_publisher, get_publisher_by_id, get_all_publishers, update_publisher_state, get_publisher_by_state

publisher_blueprint = Blueprint('publisher', __name__)

@publisher_blueprint.route('/publisher', methods=['POST'])
def create_publisher_api():
    # Parse JSON data from request
    json_data = request.json
    
    # Call the function to create a new publisher
    created_publisher = create_publisher(json_data)
    
    return jsonify({'message': 'Publisher created successfully', 
                    'publisher': created_publisher
                    }), 201


@publisher_blueprint.route('/publisher', methods=['PUT'])
def update_publisher_api():
    # Parse JSON data from request
    json_data = request.json
    
    # Update the publisher
    updated_publisher = update_publisher(json_data)
    
    if updated_publisher:
        return jsonify({
            'message': 'Publisher updated successfully',
            'publisher': updated_publisher
        }), 200
    else:
        return jsonify({'error': 'Publisher not found'}), 404

@publisher_blueprint.route('/publisher/publisherid/<publisher_id>', methods=['GET']) 
def get_publisher_api(publisher_id):
    # Get the publisher
    publisher = get_publisher_by_id(publisher_id)
    
    if publisher:
        return publisher, 200
    else:
        return jsonify({'error': 'Publisher not found'}), 404
    
@publisher_blueprint.route('/publisher', methods=['GET'])
def get_all_publishers_api():
    # Get all publishers
    publishers = get_all_publishers()
    
    return publishers, 200

@publisher_blueprint.route('/publisher', methods=['PATCH'])
def update_publisher_state_api():
    publisher_id = request.args.get('publisher_id')
    new_state = request.args.get('state')
    if new_state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    if new_state == States.CREATED.value:
        return jsonify({'error': 'Invalid State Transition'}), 400
    if update_publisher_state(publisher_id, new_state):
        return jsonify({'message': f'Publisher state updated successfully to {new_state}'}), 200
    else:
        return jsonify({'error': 'Publisher not found'}), 404
    
@publisher_blueprint.route('/publisher/state/<state>', methods=['GET'])
def get_publisher_by_state_api(state):
    if state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    publishers = get_publisher_by_state(state)
    return publishers, 200