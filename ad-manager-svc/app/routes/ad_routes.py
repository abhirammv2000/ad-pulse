from flask import request, jsonify, Blueprint
from app.enums.States import States
from app.services.ad_service import get_all_ads, create_ad, get_ad_by_id, get_ad_by_state, update_ad_state, update_ad, get_ad_by_campaign_and_advertiser_id

ad_blueprint = Blueprint('ad', __name__)

@ad_blueprint.route('/ad', methods=['GET'])
def get_all_ads_api():
    # Get all ads
    ads = get_all_ads()
    print("ads")
    return ads, 200

@ad_blueprint.route('/ad', methods=['POST'])
def create_ad_api():
    # Parse JSON data from request
    json_data = request.json

    # Call the function to create a new ad
    created_ad = create_ad(json_data)

    return jsonify({'message': 'Ad created successfully',
                    'ad': created_ad
                    }), 201

@ad_blueprint.route('/ad/adid/<ad_id>', methods=['GET'])
def get_ad_by_id_api(ad_id):
    # Get the ad
    ad = get_ad_by_id(ad_id)

    if ad:
        return ad, 200
    else:
        return jsonify({'error': 'Ad not found'}), 404

@ad_blueprint.route('/ad/state/<state>', methods=['GET'])
def get_ad_by_state_api(state):
    # Get the ad
    if state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    ads = get_ad_by_state(state)
    return ads, 200

@ad_blueprint.route('/ad', methods=['PATCH'])
def update_ad_state_api():
    ad_id = request.args.get('ad_id')
    new_state = request.args.get('state')
    print(new_state)
    if new_state not in States.__members__:
        print(States.__members__)
        return jsonify({'error': 'Invalid state'}), 400
    if new_state == States.CREATED.value:
        return jsonify({'error': 'Invalid State Transition'}), 400
    if update_ad_state(ad_id, new_state):
        return jsonify({'message': f'Ad state updated successfully to {new_state}'}), 200
    else:
        return jsonify({'error': 'Ad not found'}), 404

@ad_blueprint.route('/ad', methods=['PUT'])
def update_ad_api():
    # Parse JSON data from request
    json_data = request.json

    # Update the ad
    updated_ad = update_ad(json_data)

    if updated_ad:
        return jsonify({
            'message': 'Ad updated successfully',
            'ad': updated_ad
        }), 200
    else:
        return jsonify({'error': 'Ad not found'}), 404
    
@ad_blueprint.route('/ad/advertiser/<advertiser_id>/campaign/<campaign_id>', methods=['GET'])
def get_ad_by_campaign_and_advertiser_api(advertiser_id, campaign_id):
    # Get the ad
    ads = get_ad_by_campaign_and_advertiser_id(advertiser_id, campaign_id)
    return ads, 200