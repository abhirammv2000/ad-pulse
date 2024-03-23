import schedule
import time
from app import create_app
from app.cache.cache_job import fetch_and_cache_active_ads

def schedule_cache_job():
    app = create_app()

    # Schedule the cache population logic to run every minute
    print('Scheduling cache population job...')

    schedule.every().minute.do(fetch_and_cache_active_ads)

    # Run the scheduler continuously
    while True:
        print('Checking for pending jobs...')
        schedule.run_pending()
        print('No pending jobs found. Sleeping for 1 second.')
        time.sleep(1)

if __name__ == '__main__':
    schedule_cache_job()