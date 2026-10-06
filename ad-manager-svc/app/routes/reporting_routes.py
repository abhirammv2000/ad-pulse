from flask import Blueprint, jsonify

from app.services.reporting_service import delete_report_by_ad_id, get_report, get_report_by_ad_id

reporting_blueprint = Blueprint('reporting', __name__)


@reporting_blueprint.route('/reports', methods=['GET'])
def get_reports():
    return jsonify(get_report()), 200


@reporting_blueprint.route('/reports/<ad_id>', methods=['GET'])
def get_reports_by_ad_id(ad_id):
    return jsonify(get_report_by_ad_id(ad_id)), 200


@reporting_blueprint.route('/reports/<ad_id>', methods=['DELETE'])
def delete_reports_by_ad_id(ad_id):
    if delete_report_by_ad_id(ad_id):
        return jsonify({'message': 'Report deleted successfully'}), 200
    return jsonify({'error': 'Report not found'}), 404
