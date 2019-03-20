import os
import sys
import time
import re
import json
import book
import traceback
from slackclient import SlackClient
roompref = [15,14,13,12,16,11,10,9,8]

try:
    with open('slack.json') as f:
        token = json.load(f)
except:
    print("Error loading file")
    sys.exit(0)

starterbot_id = None
slack_client = SlackClient(token['bot_token'])
# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
BOOK_COMMAND = "book"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "Not sure what you mean. Try *{}* startHour:startMin endHour:endMin #days in the future.".format(BOOK_COMMAND)

    # Finds and executes the given command, filling in response
    response = None
    # This is where you start to implement more commands!
    if command.startswith(BOOK_COMMAND):
        try:
            startHour = int(command.split(' ')[1].rpartition(':')[0])
            startMin = int(command.split(' ')[1].rpartition(':')[2])
            endHour = int(command.split(' ')[2].rpartition(':')[0])
            endMin = int(command.split(' ')[2].rpartition(':')[2])

            try:
                if command.split(' ')[3].lower() == 'today':
                    delta = 0
                elif command.split(' ')[3].lower() == 'tomorrow':
                    delta = 1
                else:
                    delta = int(command.split(' ')[3])  
            except IndexError: #Make delta optional and use today if not provided
                delta = 0

            for i in range(1,4): # Run through all the floors
                result = book.scrapeAndBook(delta,startHour,startMin,endHour,endMin,i,roompref)
                if result == "No rooms found":
                    continue
                else:
                    response = result
                    break
            #having response = "No rooms found" at the end of the for loop wasn't working for some reason so here's the solution
            if not response:
                response = "No rooms found"
        except:
            response = "Error, try something else"

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")