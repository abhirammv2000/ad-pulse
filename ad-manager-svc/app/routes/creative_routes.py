import os

import requests
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from app.routes.helpers import change_state, invalid_body_response, json_body, list_by_state
from app.services.creative_service import (
    create_creative,
    get_all_creatives,
    get_creative_by_advertiser_id,
    get_creative_by_id,
    get_creative_by_state,
    update_creative,
    update_creative_state,
)

creative_blueprint = Blueprint('creative', __name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "Creatives")
UPLOAD_TIMEOUT_SECONDS = 30


def upload_image_to_supabase(image_file, filename):
    """Upload to Supabase storage and return its JSON reply.

    Raises requests.RequestException if storage can't be reached. A reply that
    isn't JSON comes back as {"error": <body text>}.
    """
    headers = {
        "authorization": f"Bearer {SUPABASE_KEY}",
        "api_key": SUPABASE_KEY,
    }
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{filename}"
    files = {"file": (filename, image_file, image_file.mimetype or "application/octet-stream")}
    response = requests.post(url, headers=headers, files=files, timeout=UPLOAD_TIMEOUT_SECONDS)
    try:
        return response.json()
    except ValueError:
        return {"error": response.text}


@creative_blueprint.route("/creative/upload", methods=["POST"])
def upload_image():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return jsonify({"error": "Creative storage is not configured"}), 503

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "No image selected"}), 400

    # The filename ends up in a storage URL path, so strip anything that could
    # escape the bucket folder.
    filename = secure_filename(request.args.get('filename', ''))
    if not filename:
        return jsonify({"error": "Filename not provided"}), 400

    try:
        response = upload_image_to_supabase(image_file, filename)
    except requests.RequestException:
        return jsonify({"error": "Creative storage is unreachable"}), 502

    if "error" in response:
        return jsonify({"error": "Failed to upload image", "response": response}), 400

    image_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{filename}"
    return jsonify({"image_url": image_url}), 200


@creative_blueprint.route('/creative', methods=['POST'])
def create_creative_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    return jsonify({'message': 'Creative created successfully', 'creative': create_creative(json_data)}), 201


@creative_blueprint.route('/creative', methods=['PUT'])
def update_creative_api():
    json_data = json_body()
    if json_data is None:
        return invalid_body_response()
    updated_creative = update_creative(json_data)
    if updated_creative:
        return jsonify({'message': 'Creative updated successfully', 'creative': updated_creative}), 200
    return jsonify({'error': 'Creative not found'}), 404


@creative_blueprint.route('/creative/creativeid/<creative_id>', methods=['GET'])
def get_creative_api(creative_id):
    creative = get_creative_by_id(creative_id)
    if creative:
        return jsonify(creative), 200
    return jsonify({'error': 'Creative not found'}), 404


@creative_blueprint.route('/creative', methods=['GET'])
def get_all_creatives_api():
    return jsonify(get_all_creatives()), 200


@creative_blueprint.route('/creative', methods=['PATCH'])
def update_creative_state_api():
    return change_state(update_creative_state, request.args.get('creative_id'), 'Creative')


@creative_blueprint.route('/creative/state/<state>', methods=['GET'])
def get_creative_by_state_api(state):
    return list_by_state(get_creative_by_state, state)


@creative_blueprint.route('/creative/advertiser/<advertiser_id>', methods=['GET'])
def get_creative_by_advertiser_api(advertiser_id):
    return jsonify(get_creative_by_advertiser_id(advertiser_id)), 200
