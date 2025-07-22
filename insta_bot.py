import json
import time
import re
import random
import logging
import os
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, RateLimitError, ClientError
from datetime import datetime, UTC

# Set up logging
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error("config.json not found")
    print("Error: config.json not found")
    exit()

USERNAME = config['username']
PASSWORD = config['password']
PROXY = config['proxy'] if config['proxy'] else None
POST_CHECK_INTERVAL_MIN = config['post_check_interval'][0]
POST_CHECK_INTERVAL_MAX = config['post_check_interval'][1]
REPLY_VARIATIONS = config['reply_variations']
SESSION_FILE = 'session.json'

# Initialize deployment timestamp (timezone-aware)
DEPLOYMENT_TIMESTAMP = datetime.now(UTC).timestamp()

# Initialize Instagrapi client
cl = Client()
if PROXY:
    cl.set_proxy(PROXY)

# Function to re-login and save session
def re_login():
    global cl
    try:
        cl.login(USERNAME, PASSWORD)
        cl.dump_settings(SESSION_FILE)
        logging.info("Re-logged in successfully and saved session")
        print("Re-logged in successfully and saved session")
        time.sleep(5)  # Brief delay to stabilize session
    except Exception as e:
        logging.error(f"Re-login failed: {e}")
        print(f"Re-login failed: {e}")
        time.sleep(300)  # Wait 5 minutes before retrying on failure
        raise

# Load session if exists
if os.path.exists(SESSION_FILE):
    try:
        cl.load_settings(SESSION_FILE)
        cl.login(USERNAME, PASSWORD, relogin=False)
        logging.info("Loaded session and logged in")
        print("Loaded session and logged in")
    except Exception as e:
        logging.error(f"Session login failed: {e}")
        print(f"Session login failed: {e}")
        re_login()

# Log in to Instagram if no session or login failed
if not cl.user_id:
    re_login()

# Function to check if comment is emoji-only
def is_emoji_only(comment):
    comment = comment.strip()
    emoji_pattern = re.compile(r'^[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\s]*$')
    return bool(emoji_pattern.match(comment))

# Function to reply to new comments
def reply_to_comments(media_id):
    try:
        comments = cl.media_comments(media_id)
        for comment in comments:
            if (comment.created_at_utc.timestamp() >= DEPLOYMENT_TIMESTAMP and
                not is_emoji_only(comment.text) and
                comment.user.username != USERNAME):
                reply_text = random.choice(REPLY_VARIATIONS)
                cl.media_comment(media_id, reply_text, replied_to_comment_id=comment.pk)
                logging.info(f"Replied to new comment by {comment.user.username}: {comment.text}")
                print(f"Replied to new comment by {comment.user.username}: {comment.text}")
                time.sleep(random.uniform(5, 15))
    except RateLimitError:
        logging.warning("Rate limit hit. Sleeping for 15 minutes.")
        print("Rate limit hit. Sleeping for 15 minutes.")
        time.sleep(900)
    except ClientError as e:
        if "login_required" in str(e).lower():
            logging.warning("Login required detected, attempting re-login")
            print("Login required detected, attempting re-login")
            re_login()
        else:
            logging.error(f"Error processing comments: {e}")
            print(f"Error processing comments: {e}")

# Main loop with continuous checking
while True:
    try:
        user_id = cl.user_id_from_username(USERNAME)
        medias = cl.user_medias(user_id, amount=100)
        for media in medias:
            logging.info(f"Checking comments for post: {media.pk}")
            print(f"Checking comments for post: {media.pk}")
            reply_to_comments(media.pk)
            time.sleep(random.uniform(10, 20))
        logging.info("Completed post check cycle")
        print("Completed post check cycle")
        time.sleep(random.uniform(POST_CHECK_INTERVAL_MIN, POST_CHECK_INTERVAL_MAX))
    except LoginRequired:
        logging.warning("Session expired. Re-logging in.")
        print("Session expired. Re-logging in.")
        re_login()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        time.sleep(900)