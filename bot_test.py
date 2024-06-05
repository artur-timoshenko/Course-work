from imports import *


TOKEN_FILE = "token.json"
BANNED_PHRASES_FILE = "banned_phrases.json"
BANNED_PHRASES_FILE_NEW = "banned_phrases_new.json"
WARNING_PHRASES_FILE = "warning_phrases.json"
BANSTAT_FILE = "ban_stat.json"
BOT_STAT_FILE = "bot_stat.json"
ADMINLIST_FILE = "adminlist.json"


DELETE_MESSAGE_DELAY = 5


message_count = 3


message_occurrences_cache = {}


MUTE_DURATION = 1209600


logging.basicConfig(filename='Telebot.json', encoding='utf-8', level=logging.INFO,
                    format='%(levelname)s - %(asctime)s - %(name)s - %(message)s')


replacement_dict = {'e': 'е', 'y': 'у', 'u': 'и', 'o': 'о', 'p': 'р', 'a': 'а', 'k': 'к', 'x': 'х', 'c': 'с',
                    'n': 'п', 'm': 'т', 't': 'т', 'b': 'б', 'ё': 'е', '0':'о', '6':'б'}
translation_table = str.maketrans(replacement_dict)


def read_token_and_chat_id():
    try:
        with open(TOKEN_FILE, "r") as file:
            data = json.load(file)
            token = data.get("token")
            chat_id = data.get("chat_id")
        if token is not None and chat_id is not None:  
            return token, chat_id
        else:
            print(f"Error: Failed to get token and/or chat ID from file'{TOKEN_FILE}'.")
            logging.error(f"Error: Failed to get token and/or chat ID from file '{TOKEN_FILE}'.")
            return None, None
    except FileNotFoundError:
        print(f"File '{TOKEN_FILE}' not found.")
        logging.error(f"File '{TOKEN_FILE}' not found.")
        return None, None
    except json.JSONDecodeError:
        print(f"Error reading file '{TOKEN_FILE}': invalid JSON format")
        logging.error(f"Error reading file '{TOKEN_FILE}': invalid JSON format")
        return None, None

def write_data_to_file(filename, data):
    with open(filename, "a", encoding="utf-8") as file:
        try:
            file.write(str(data) + "\n")
        except Exception as e:
            print(f"Error writing data to file: {e}")
            logging.error(f"Error writing data to file: {e}")


def read_data_from_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = [line.strip().lower() for line in file]
    except FileNotFoundError:
        print(f"File '{filename}' not found.")
        logging.error(f"File '{filename}' not found.")
        data = []
    return data


def record_ban_event(user_id, user_name, message_text, phrase, event_type):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": current_time,
        "user_id": user_id,
        "user_name": user_name,
        "ban_phrase": phrase,
        "message_text": message_text,
        "event_type": event_type}
    with open(BANSTAT_FILE, "a", encoding="utf-8") as file:
        try:
            json.dump(entry, file, ensure_ascii=False)
            file.write("\n")
        except Exception as e:
            print(f"Error writing data to file: {e}")
            logging.error(f"Error writing data to file:{e}")
    return BANSTAT_FILE


def record_bot_add_event(user_id, user_name, bot_id, bot_name):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": current_time,
        "user_id": user_id,
        "user_name": user_name,
        "bot_id": bot_id,
        "bot_name": bot_name}
    with open(BOT_STAT_FILE, "a", encoding="utf-8") as file:
        try:
            json.dump(entry, file, ensure_ascii=False)
            file.write("\n")
        except Exception as e:
            print(f"Error writing data to file: {e}")
            logging.error(f"Error writing data to file: {e}")

def clear_file(filename):
    with open(filename, "w"):
        pass


TOKEN, CHAT_ID = read_token_and_chat_id()


bot = telebot.TeleBot(TOKEN)


bot.skip_pending = False


BOT_ID = bot.get_me().id


def get_chat_admins(chat_id):
    admins = []
    try:
        chat_admins = bot.get_chat_administrators(chat_id)
        for admin in chat_admins:
            admins.append(str(admin.user.id))
    except Exception as e:
        print("Error getting chat administrators:", e)
    return admins


def delete_message_after_delay(chat_id, message_id, delay):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print("Failed to delete message", e)


def preprocess_text(text):
    
    text = re.sub(r'[^\w\s]', '', text)
    
    text = re.sub(r'\s+', ' ', text)

    
    words = text.split()
    result = []
    for word in words:
        
        if all(char.isalpha() and re.match('[a-z]', char.lower()) for char in word):
            
            result.append(word)
        else:
            
            result.append(word.translate(translation_table))
    return ' '.join(result)


def count_message_occurrences(text):
    count = 0
    
    if text in message_occurrences_cache:
        return message_occurrences_cache

    with open(BANSTAT_FILE, "r", encoding="utf-8") as file:
        for line in file:
            entry = json.loads(line)
            if entry.get("message_text") == text:
                count += 1
            if count >= message_count:
                
                message_occurrences_cache[text] = count
                return message_occurrences_cache


def log_and_admin_message(notification_message):
    logging.info(notification_message)
    for admin_id in admin_ids:
        if str(admin_id) == str(BOT_ID):
            continue
        try:
            bot.send_message(admin_id, notification_message)
            logging.info(f'Send {admin_id}')
        except telebot.apihelper.ApiException as e:
            logging.error(f"Failed to send {admin_id}: {e}")

def log_error(e):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Error: {e}")
    logging.error(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Error: {e}")
    time.sleep(10)  


def recognize_text(image_stream):
    
    image = Image.open(image_stream)
    
    extracted_text = pytesseract.image_to_string(image)

    return extracted_text


def check_suspicious_text(text, banned_phrases_new):
    found_words = [word.lower() for word in banned_phrases_new if word.lower() in text.lower()]
    found_count = len(found_words)
    total_words = len(text.split())  
    suspicious_percentage = round((found_count / total_words) * 100, 2) if total_words > 0 else 0
    suspicious = suspicious_percentage > 30
    return suspicious, found_count, found_words, suspicious_percentage


admin_ids = get_chat_admins(CHAT_ID)


banned_phrases = read_data_from_file(BANNED_PHRASES_FILE)
banned_phrases_new = read_data_from_file(BANNED_PHRASES_FILE_NEW)


warning_phrases = read_data_from_file(WARNING_PHRASES_FILE)


admin_list = [CHAT_ID] + admin_ids


clear_file(ADMINLIST_FILE)


write_data_to_file(ADMINLIST_FILE, "\n".join(admin_list))


@bot.message_handler(commands=["start", "help", "settings", "any_other_command"])
def handle_commands(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_text = message.text.strip()

    
    if str(user_id) in admin_ids:
        if str(message_text == "/start"):
            # Создаем клавиатуру
            keyboard = types.ReplyKeyboardMarkup(row_width=2)
            button_texts = ["Add data to BAN", "Add data to WARNING", "Statistics", "Status"]
            for text in button_texts:
                button = types.KeyboardButton(text=text)
                keyboard.add(button)
            
            try:
                bot.send_message(user_id, "Choose an action:", reply_markup=keyboard)
            except ApiTelegramException as e:
                if e.error_code == 403:
                    bot.send_message(chat_id, "To work with a bot, please allow receiving messages from bots in Telegram's privacy settings.")
                else:
                    bot.send_message(chat_id, f"An error has occurred: {e}")
    if str(message_text) == "/start":
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception as e:
            log_error(e)


@bot.message_handler(func=lambda message: message.text.strip() == "Add data to BAN")
def add_to_ban_phrases(message):
    user_id = message.from_user.id

    if str(user_id) in admin_ids:
        bot.send_message(user_id, "Enter text to add to BAN")
        bot.delete_message(message.chat.id, message.message_id)
        bot.register_next_step_handler(message, process_ban_phrase, user_id)


def process_ban_phrase(message, user_id):
    global banned_phrases
    notification_massege = []
    user_name = message.from_user.first_name
    lines = message.text.splitlines()

    for line in lines:
        new_phrase = preprocess_text(line)

    
        write_data_to_file(BANNED_PHRASES_FILE, new_phrase)
        logging.info(f'{user_id} {user_name} added the phrase "{new_phrase}" to BAN')
        notification_massege.append(new_phrase)

    
    bot.send_message(user_id, f"The phrase\n{notification_massege}\n was successfully added to the BAN.")
    banned_phrases = read_data_from_file(BANNED_PHRASES_FILE)
    return banned_phrases


@bot.message_handler(func=lambda message: message.text.strip() == "Add data to WARNING")
def add_to_warning_phrases(message):
    user_id = message.from_user.id

    if str(user_id) in admin_ids:
        bot.send_message(user_id, "Enter text to add to WARNING:")
        bot.delete_message(message.chat.id, message.message_id)
        bot.register_next_step_handler(message, process_warning_phrase, user_id)


def process_warning_phrase(message, user_id):
    global warning_phrases
    new_phrase = message.text.strip()
    user_name = message.from_user.first_name

    
    write_data_to_file(WARNING_PHRASES_FILE, new_phrase)

    
    bot.send_message(user_id, f"The phrase\n'{new_phrase}'\n successfully added to WARNING.")
    logging.info(f'{user_id} {user_name} added the phrase "{new_phrase}" to Warning')
    warning_phrases = read_data_from_file(WARNING_PHRASES_FILE)

    return warning_phrases


@bot.message_handler(func=lambda message: message.text.strip() == "Statistics")
def handle_statistics(message):
    user_id = message.from_user.id
    if str(user_id) in admin_ids:
        bot.send_message(user_id,"Enter the date range to display statistics in the format 'yyyy-mm-dd yyyy-mm-dd', for example, '2024-02-01 2024-02-07':")
        bot.delete_message(message.chat.id, message.message_id)
        bot.register_next_step_handler(message, process_dates)


def process_dates(message):
    date_range = message.text.split()
    chat_id = message.chat.id
    if len(date_range) == 1:
        start_date = end_date = date_range[0]
    elif len(date_range) == 2:
        start_date, end_date = date_range
    else:
        bot.send_message(chat_id, "Invalid input format. Try again.")
        return

    file_path = BANSTAT_FILE
    file_bot_path = BOT_STAT_FILE
    count_ban, count_warning, count_bot, count_mut = count_events(file_path, file_bot_path, start_date, end_date)
    bot.send_message(chat_id, f"For the period from {start_date} to {end_date}:\n"
                                      f"Promotional {count_ban} messages,\n"
                                      f"{count warning} warning issued,\n"
                                      f"banned {count_mut},\n"
                                      f"Banned {count_bot} bots")


def count_events(file_path, file_bot_path, start_date, end_date):
    count_ban = 0
    count_warning = 0
    count_bot = 0
    count_mut = 0
    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d') if end_date else start_datetime
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            event_data = json.loads(line)
            timestamp = datetime.strptime(event_data['timestamp'][:10], '%Y-%m-%d')
            if start_datetime <= timestamp <= end_datetime:
                if event_data['event_type'] == 'BAN':
                    count_ban += 1
                elif event_data['event_type'] == 'WARNING':
                    count_warning += 1
                elif event_data['event_type'] == 'MUT':
                    count_mut += 1
    with open(file_bot_path, 'r', encoding='utf-8') as file:
        for line in file:
            event_data = json.loads(line)
            timestamp = datetime.strptime(event_data['timestamp'][:10], '%Y-%m-%d')
            if start_datetime <= timestamp <= end_datetime:
                count_bot += 1
    return count_ban, count_warning, count_bot, count_mut


@bot.message_handler(func=lambda message: message.text.strip() == "Статус")
def status_command(message):
    user_id = message.from_user.id

    if str(user_id) in admin_ids:
        
        bot.send_message(user_id, f"Bot status: online\nBot launch time: {bot_start_time}")
        bot.delete_message(message.chat.id, message.message_id)


@bot.message_handler(content_types=['photo', 'audio', 'documents', 'video', 'voice', 'sticker'])
def handle_photo(message):
    
    if message.caption:
        message_text = message.caption
#    if message.photo:
#        file_id = message.photo[-1].file_id
#        file_info = bot.get_file(file_id)
#        image_stream = BytesIO()
#        file_info.download(out=image_stream)
#        image_stream.seek(0)
#
#        extracted_text = recognize_text(image_stream)
#
#        message_text.append(f"Text from the picture: '{extracted_text}'")

        handle_text_messages(message, message_text)


@bot.message_handler(func=lambda message: True)
def handle_text_messages(message, message_text=None):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    chat_id = message.chat.id
    message_id = message.message_id
    words = ()


    if str(user_id) in admin_ids:
        return


    if message_text is None:
        message_text = message.text
        if message_text is None:
            return


    logging.info(f"{user_name}, {message_text}")
    suspicious, found_count, found_words, suspicious_percentage = check_suspicious_text(preprocess_text(message_text), banned_phrases_new)
    if suspicious:
        logging.info(f"!!! !!! Not OK. Number of matching words: {found_count}, {suspicious_percentage}%")
        logging.info(f"Matched words: {', '.join(found_words)}")
    else:
        logging.info(f"OK. Number of matching words: {found_count}, {suspicious_percentage}%")
        logging.info(f"Matched words: {', '.join(found_words)}")



    if count_message_occurrences(message_text):
        bot.delete_message(chat_id, message_id)
        notification_message = f"User {user_name} (ID: {user_id}) sent a duplicate message:\n'{message_text}'\nI muted him up for 14 days"
        record_ban_event(user_id, user_name, message_text,'repeat message',"MUT")
        log_and_admin_message(notification_message)
        #bot.kick_chat_member(CHAT_ID, user_id)
        bot.restrict_chat_member(chat_id, user_id, until_date = time.time() + MUTE_DURATION, can_send_messages=False)
        logging.info(f"User {user_name} ID: {user_id}, blocked for 14 days")
        return


    text = preprocess_text(message_text)


    for phrase in banned_phrases:
        words = phrase.split()
        found = all(word.lower() in text.lower() for word in words)
        if found:
            ban_message = f"I suspect that {user_name} (ID: {user_id}) sent an advertisement, this message has no place in this chat!"
            bot.delete_message(chat_id, message_id)
            record_ban_event(user_id, user_name, message_text, phrase,"BAN")
            sent_message = bot.send_message(chat_id, ban_message)
            notification_message = f"Message from user {user_name} (ID: {user_id}) deleted for sending advertisement\nPhrase:\n'{phrase}'\nUser message\n'{message_text}'"
            log_and_admin_message(notification_message)
            threading.Thread(target=delete_message_after_delay, args=(sent_message.chat.id, sent_message.message_id, DELETE_MESSAGE_DELAY)).start()
            break


    if not found:
        for phrase in warning_phrases:
            words = phrase.split()
            found = any(len(word) == len(word.lower()) and word.lower() in text.split() for word in words)
            if found:
                warning_message = f"User {user_name} (ID: {user_id}) your message contained the word {phrase} that is prohibited in this chat, try writing it differently."
                bot.delete_message(chat_id, message_id)
                record_ban_event(user_id, user_name, message_text, phrase,"WARNING")
                sent_message = bot.send_message(chat_id, warning_message)
                notification_message = f"Message from user {user_name} (ID: {user_id}) deleted for sending a message with obscenities:\nWord:\n{phrase}\nUser message:\n'{message_text}'"
                log_and_admin_message(notification_message)
                threading.Thread(target=delete_message_after_delay, args=(sent_message.chat.id, sent_message.message_id, DELETE_MESSAGE_DELAY)).start()
                break


@bot.message_handler(content_types=['new_chat_members', 'left_chat_member', 'new_chat_title', 'new_chat_photo',
                                    'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created',
                                    'channel_chat_created', 'migrate_to_chat_id', 'migrate_from_chat_id'])
def delete(message):
    try:
        if message.content_type == 'new_chat_members':
            for new_chat_member in message.new_chat_members:
                if new_chat_member.is_bot:
                    # Попытка выгнать бота из чата
                    bot.kick_chat_member(message.chat.id, new_chat_member.id)
                    # Получение информации о пользователе, попытка записи события
                    user_id = message.from_user.id
                    user_name = message.from_user.first_name + ' ' + message.from_user.last_name
                    bot_id = new_chat_member.id
                    bot_name = new_chat_member.username
                    record_bot_add_event(user_id, user_name, bot_id, bot_name)
                    notification_message = f"User {user_name} (ID: {user_id}) tried to add a bot:\n'{bot_name}'"
                    log_and_admin_message(notification_message)

        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:

        print(f"An error has occurred: {e}")
        logging.error(f"An error has occurred: {e}")


while True:
    try:
        bot_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat_title = bot.get_chat(CHAT_ID).title
        print(f"Bot started at {bot_start_time} in chat {chat_title}")
        logging.info(f"Bot started {bot_start_time} in chat ID{CHAT_ID}, {chat_title}")

        admins_list = []
        for admin_id in admin_ids:
            admin_info = bot.get_chat_member(CHAT_ID, user_id = admin_id)
            admin_name = admin_info.user.first_name
            admin_last_name = admin_info.user.last_name
            if admin_last_name == None:
                admin_last_name = ''
            admins_list.append(admin_name + ' ' + admin_last_name)
        print(f'Admins {admins_list}')
        bot.polling(timeout=320, none_stop=True)
        time.sleep(5)  


    except telebot.apihelper.ApiTelegramException as e:
        log_error(e)
    except Exception as e:
        log_error(e)
