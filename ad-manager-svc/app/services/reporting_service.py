from pymongo import MongoClient
from flask import jsonify

# Connect to the MongoDB server
client = MongoClient("mongodb+srv://nihalsreenivasu:bMyx3JQLZ5Mj85Fx@adpulse-engagement.4du8wij.mongodb.net/?retryWrites=true&w=majority")

# Access the ad_pulse database
db = client.ad_pulse

# Access the reports collection
collection = db.reports

def get_report():
    reports = list(collection.find({}))
    return jsonify(reports)

def get_report_by_ad_id(ad_id):
    reports = list(collection.find({'_id': ad_id}))
    return jsonify(reports)

def delete_report_by_ad_id(ad_id):
    result = collection.delete_one({'_id': ad_id})
    print(result)
    return True