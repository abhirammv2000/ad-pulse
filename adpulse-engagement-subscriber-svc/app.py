from google.cloud import pubsub_v1
from google.oauth2 import service_account
import json
from pymongo.mongo_client import MongoClient
from time import sleep

project_id = "ad-pulse-team1"
subscription_id_clk = "click-service-topic-sub"
subscription_id_render = "csc-service-topic-sub"

# Set the path to your service account key file (outside the loop)
key_path = "./ad-pulse-team1-dbdee446d2a9.json"

# Create credentials object from the service account key file (once)
credentials = service_account.Credentials.from_service_account_file(key_path)

subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
subscription_path_clk = subscriber.subscription_path(project_id, subscription_id_clk)
subscription_path_csc = subscriber.subscription_path(project_id, subscription_id_render)

def create_session():
    uri = "mongodb+srv://nihalsreenivasu:bMyx3JQLZ5Mj85Fx@adpulse-engagement.4du8wij.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    try:
        client.admin.command('ping')
    except Exception as e:
        print(e)

    return client

def update_db(ad_id, type):
    session = create_session()

    # Check if the ad_id already exists in the collection
    try:
        existing_row = session.ad_pulse.reports.find_one({"_id": ad_id})
    except Exception as e:
        print(f"Error querying the database: {e}")
        return

    if existing_row:
        # If the ad_id exists, update the count
        count = existing_row[type] + 1
        session.ad_pulse.reports.update_one({"_id": ad_id}, {"$set": {type: count}})
        print(f"Updated {type} count for ad_id {ad_id} to {count}")
    else:
        # If the ad_id doesn't exist, add a new row
        if type == "click":
            new_row = {"_id": ad_id, "click": 1, "render": 0}
        else: 
            new_row = {"_id": ad_id, "click": 0, "render": 1}
        session.ad_pulse.reports.insert_one(new_row)

    session.close()

# Rest of the code...
def callbackClk(message):
    print(f"Received message: {message.data.decode()}")
    msg = message.data.decode()
    try:
        json_data = json.loads(msg)
        update_db(json_data['adid'], "click")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    message.ack()

def callbackCsc(message):
    print(f"Received message: {message.data.decode()}")
    msg = message.data.decode()
    try:
        json_data = json.loads(msg)
        update_db(json_data['adid'], "render")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    message.ack()


subscriber.subscribe(subscription_path_clk, callback=callbackClk)
subscriber.subscribe(subscription_path_csc, callback=callbackCsc)

print(f"Listening for messages on {subscription_path_clk} and {subscription_path_csc} ...")

# Keep the main thread alive by entering an infinite loop
while True:
    sleep(0.5)
    pass  # Do nothing, just keep the script running
