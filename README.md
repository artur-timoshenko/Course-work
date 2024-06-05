This bot is designed to moderate messages in Telegram chats. It automatically deletes messages containing banned phrases and keeps statistics on banned and warned users.


Peculiarities:

1. Moderation of messages:
The bot automatically deletes messages containing banned phrases/words that are specified in the banned_phrases.json and warning_phrases.json files.
When a violation is detected, the bot sends a notification to the chat. At the testing stage, the user BAN is not applied. Lists of phrases are replenished and updated. Current peaks are used for testing only

3. Deleting service messages:
The bot deletes messages about joining and leaving the chat, changing the chat name and other service messages that are not relevant to users.

4. Does not allow you to invite a bot to a group:
When a bot is added to a group, the bot is removed, and the bot itself is included in the statistics of violators.

5. Statistics:
The bot keeps statistics on banned and warned users, recording data in the banstat.json file.
Statistics include the number of messages banned and warnings issued, along with the date and time of the event. Separate statistics are kept for those who added bots to the group.

6. Checking repeated messages:
If a message appears in the ban_stat file four or more times, it goes into the bot's cache, the message from the user is deleted, and the user is banned. Next, the cache is checked and if it is not in the cache, then the file is banned_stat, the conditions are as described above. All actions are logged, and a message about the ban is sent to administrators.

Control.

- Bot administration:
Chat administrators can use the /start command to bring up the bot management menu and view statistics.

- Adding new phrases:
Administrators can add new banned and warning phrases through bot commands.

- Call statistics:
When you enter a date or date range in the specified format, the bot sends a message about the number of WARNING and BAN events for the selected period of time or for the specified date.

- Status request:
In response, the bot sends a message when it was launched.