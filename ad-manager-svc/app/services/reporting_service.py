import os

from flask import jsonify
from pymongo import MongoClient

_collection = None


def _reports():
    """Return the `reports` collection, connecting on first use."""
    global _collection
    if _collection is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI is not set")
        client = MongoClient(uri)
        _collection = client[os.getenv("MONGODB_DATABASE", "ad_pulse")].reports
    return _collection


def get_report():
    return jsonify(list(_reports().find({})))


def get_report_by_ad_id(ad_id):
    return jsonify(list(_reports().find({'_id': ad_id})))


def delete_report_by_ad_id(ad_id):
    result = _reports().delete_one({'_id': ad_id})
    return result.deleted_count > 0
