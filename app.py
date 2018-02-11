import json
import logging
import os
import random

import requests

GCP_KEY = os.environ["GCP_KEY"]
SLACK_OAUTH_TOKEN = os.environ["SLACK_OAUTH_TOKEN"]

with open("./emoji.json") as f:
    EMOJI_LIST = json.load(f)

logger = logging.getLogger()


def analyze_sentiment(text: str) -> str:
    """Analyze sentiment with Google Cloud Natural Language API.

    Args:
        text (str): Target text

    Returns:
        str: Result of classifying sentiment into 4 classes
    """
    url = f"https://language.googleapis.com/v1/documents:analyzeSentiment?key={GCP_KEY}"
    payload = {"document": {"type": "PLAIN_TEXT", "content": text}, "encodingType": "UTF8"}

    r = requests.post(url=url, data=json.dumps(payload))
    logger.info(f"[Cloud Natural Language API] status_code: {r.status_code}, text: {r.text}")

    sentiment = r.json()["documentSentiment"]
    score, magnitude = sentiment["score"], sentiment["magnitude"]
    logger.info(f"[Cloud Natural Language API] score: {score}, magnitude: {magnitude}")

    if score >= 0:
        if magnitude > 1.0:
            return "positive_high"
        else:
            return "positive_low"
    else:
        if magnitude > 1.0:
            return "negative_high"
        else:
            return "negative_low"


def pick_emoji(sentiment_class: str) -> str:
    """ Randomly pick emoji to send.

    Args:
        sentiment_class (int): Class of sentiment

    Returns:
        str: Emoji ID
    """
    return random.choice(EMOJI_LIST[sentiment_class])


def handler(request):
    body = request.get_json()

    # url_verification
    if "challenge" in body:
        logger.info(f"[Slack API] url_verification {body}")
        return body.get("challenge")

    event = body.get("event")
    logger.info(f"event: {event}")

    if "bot_id" not in event.keys():
        return

    sentiment_class = analyze_sentiment(text=event["text"])

    # put stamp to the post on Slack
    url = "https://slack.com/api/reactions.add"
    payload = {
        "token": SLACK_OAUTH_TOKEN,
        "name": pick_emoji(sentiment_class),
        "channel": event["channel"],
        "timestamp": event["ts"],
    }

    r = requests.post(url=url, data=payload)
    logger.info(f"[Slack API] status_code: {r.status_code}, text: {r.text}")

    # post warning message (for long sentence)
    if len(event["text"]) >= 180:
        url = "https://slack.com/api/chat.postMessage"
        payload = {
            "token": SLACK_OAUTH_TOKEN,
            "channel": event["channel"],
            "text": "The post is too long!",
        }

        r = requests.post(url=url, data=payload)
        logger.info(f"[Slack API] status_code: {r.status_code}, text: {r.text}")

    return "ok"
