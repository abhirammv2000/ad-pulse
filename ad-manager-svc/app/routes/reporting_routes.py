from app.services.reporting_service import get_report, get_report_by_ad_id, delete_report_by_ad_id
from flask import Blueprint

reporting_blueprint = Blueprint('reporting', __name__)

@reporting_blueprint.route('/reports', methods=['GET'])
def get_reports():
    reports = get_report()
    return reports

@reporting_blueprint.route('/reports/<ad_id>', methods=['GET'])
def get_reports_by_ad_id(ad_id):
    reports = get_report_by_ad_id(ad_id)
    return reports

@reporting_blueprint.route('/reports/<ad_id>', methods=['DELETE'])
def delete_reports_by_ad_id(ad_id):
    result = delete_report_by_ad_id(ad_id)
    if result:
        return 'Report deleted successfully', 200
    