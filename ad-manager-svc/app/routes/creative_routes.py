import os

from flask import request, jsonify, Blueprint
import requests
from werkzeug.utils import secure_filename
from app.enums.States import States
from app.services.creative_service import create_creative, update_creative, get_creative_by_id, get_all_creatives, update_creative_state, get_creative_by_state, get_creative_by_advertiser_id

creative_blueprint = Blueprint('creative', __name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "Creatives")

def upload_image_to_supabase(image_file, filename):
    headers = {
        "authorization": f"Bearer {SUPABASE_KEY}",
        "api_key": SUPABASE_KEY
    }
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{filename}"
    files = {"file": (filename, image_file, image_file.mimetype or "application/octet-stream")}
    response = requests.post(url, headers=headers, files=files, timeout=30)
    return response.json()

@creative_blueprint.route("/creative/upload", methods=["POST"])
def upload_image():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return jsonify({"error": "Creative storage is not configured"}), 503

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "No image selected"}), 400

    # Get the filename argument from the request. It lands in a storage URL
    # path, so strip anything that could escape the bucket folder.
    filename = secure_filename(request.args.get('filename', ''))
    if not filename:
        return jsonify({"error": "Filename not provided"}), 400

    response = upload_image_to_supabase(image_file, filename)
    if "error" in response:
        return jsonify({"error": "Failed to upload image", "response": response}), 400

    # Return the URL of the uploaded image
    image_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{filename}"
    return jsonify({"image_url": image_url}), 200

@creative_blueprint.route('/creative', methods=['POST'])
def create_creative_api():
    json_data = request.json
    created_creative = create_creative(json_data)
    
    return jsonify({'message': 'Creative created successfully', 
                    'creative': created_creative
                    }), 201

@creative_blueprint.route('/creative', methods=['PUT'])
def update_creative_api():
    json_data = request.json
    updated_creative = update_creative(json_data)
    
    if updated_creative:
        return jsonify({
            'message': 'Creative updated successfully',
            'creative': updated_creative
        }), 200
    else:
        return jsonify({'error': 'Creative not found'}), 404

@creative_blueprint.route('/creative/creativeid/<creative_id>', methods=['GET']) 
def get_creative_api(creative_id):
    creative = get_creative_by_id(creative_id)
    
    if creative:
        return jsonify(creative), 200
    else:
        return jsonify({'error': 'Creative not found'}), 404
    
@creative_blueprint.route('/creative', methods=['GET'])
def get_all_creatives_api():
    creatives = get_all_creatives()
    
    return jsonify(creatives), 200

@creative_blueprint.route('/creative', methods=['PATCH'])
def update_creative_state_api():
    creative_id = request.args.get('creative_id')
    new_state = request.args.get('state')
    if new_state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    if new_state == States.CREATED.value:
        return jsonify({'error': 'Invalid State Transition'}), 400
    if update_creative_state(creative_id, new_state):
        return jsonify({'message': f'Creative state updated successfully to {new_state}'}), 200
    else:
        return jsonify({'error': 'Creative not found'}), 404
    
@creative_blueprint.route('/creative/state/<state>', methods=['GET'])
def get_creative_by_state_api(state):
    if state not in States.__members__:
        return jsonify({'error': 'Invalid state'}), 400
    creatives = get_creative_by_state(state)
    return jsonify(creatives), 200

@creative_blueprint.route('/creative/advertiser/<advertiser_id>', methods=['GET'])
def get_creative_by_advertiser_api(advertiser_id):
    creatives = get_creative_by_advertiser_id(advertiser_id)
    return jsonify(creatives), 200
