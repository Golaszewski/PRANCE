import os
import slack

client = slack.WebClient(token="xoxb-508776780500-908334410592-5YepD426iF3yS3b5V7ZAFePM")

def slack_msg_to_prance_general(message):
    client.chat_postMessage(channel="GRH7PU4RW", text=message)
