from flask import request, jsonify, Blueprint
from app.enums.States import States
from app.services.campaign_service import get_all_campaigns, get_campaign_by_id, get_campaign_by_state, create_campaign, update_campaign, update_campaign_state, get_campaign_by_advertiser_id

campaign_blueprint = Blueprint('campaign', __name__)


@campaign_blueprint.route('/campaign', methods=['GET'])
def get_all_campaigns_api():
    # Get all campaigns
    campaigns = get_all_campaigns()

    return campaigns, 200


@campaign_blueprint.route('/campaign/<campaignid>', methods=['GET'])
def get_campaign_by_id_api(campaignid):
    # Get campaign by ID
    campaign = get_campaign_by_id(campaignid)

    if campaign is None:
        return jsonify({'error': 'Campaign not found'}), 404

    return campaign, 200


@campaign_blueprint.route('/campaign/state/<state>', methods=['GET'])
def get_campaign_by_state_api(state):
    # Get campaign by state
    campaigns = get_campaign_by_state(state)

    return campaigns, 200


@campaign_blueprint.route('/campaign', methods=['POST'])
def create_campaign_api():
    # Create campaign
    json_data = request.json
    created_campaign = create_campaign(json_data)
    # print("!!!!!!!!!!!!!!!!!!")
    # print(created_campaign)
    return jsonify({'message': 'Campaign created',
                    'campaign': created_campaign
                    }), 201

@campaign_blueprint.route('/campaign', methods=['PUT'])
def update_campaign_api():
    # Update campaign
    json_data = request.json
    updated_campaign = update_campaign(json_data)

    if updated_campaign is None:
        return jsonify({'error': 'Campaign not found'}), 404

    return jsonify({'message': 'Campaign updated',
                    'campaign': updated_campaign
                    }), 200

@campaign_blueprint.route('/campaign', methods=['PATCH'])
def update_campaign_state_api():
    campaign_id = request.args.get('campaign_id')
    new_state = request.args.get('state')
    if new_state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    if new_state == States.CREATED.value:
        return jsonify({'error': 'Invalid State Transition'}), 400
    if update_campaign_state(campaign_id, new_state):
        return jsonify({'message': f'Campaign state updated successfully to {new_state}'}), 200
    else:
        return jsonify({'error': 'Campaign not found'}), 404
    
@campaign_blueprint.route('/campaign/advertiser/<advertiser_id>', methods=['GET'])
def get_campaign_by_advertiser_api(advertiser_id):
    # Get campaign by advertiser ID
    campaigns = get_campaign_by_advertiser_id(advertiser_id)

    return campaigns, 200