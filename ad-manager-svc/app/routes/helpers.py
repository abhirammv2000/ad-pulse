"""Request handling shared by the entity routes.

Every entity (ad, campaign, creative, ad unit, publisher, advertiser) has the same
state endpoints and the same JSON body rules, so they live here once.
"""

from flask import jsonify, request

from app.enums.states import States


def json_body():
    """Return the request body if it is a JSON object, else None."""
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


def invalid_body_response():
    return jsonify({'error': 'Request body must be a JSON object'}), 400


def is_valid_state(state):
    return state in States.__members__


def invalid_state_response():
    return jsonify({'error': 'Invalid state'}), 400


def list_by_state(fetch, state):
    """GET /<entity>/state/<state>: 400 for an unknown state, else the matching rows."""
    if not is_valid_state(state):
        return invalid_state_response()
    return jsonify(fetch(state)), 200


def change_state(update, entity_id, label):
    """PATCH /<entity>?<id>=...&state=...

    The state comes from the query string. An entity can never go back to CREATED.
    `update` returns False when the id does not exist.
    """
    new_state = request.args.get('state')
    if not is_valid_state(new_state):
        return invalid_state_response()
    if new_state == States.CREATED.value:
        return jsonify({'error': 'Invalid State Transition'}), 400
    if update(entity_id, new_state):
        return jsonify({'message': f'{label} state updated successfully to {new_state}'}), 200
    return jsonify({'error': f'{label} not found'}), 404
