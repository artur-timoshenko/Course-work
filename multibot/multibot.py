from imports import *


TOKEN_FILE = "token.json"
BANNED_PHRASES_FILE = "banned_phrases.json"

WARNING_PHRASES_FILE = "warning_phrases.json"
BANSTAT_FILE = "ban_stat.json"
BOT_STAT_FILE = "bot_stat.json"


DELETE_MESSAGE_DELAY = 5

#Количество повторяющихся сообщений
message_count = 3

#Определяем словарь для кэширования сообщений
message_occurrences_cache = {}

#Если используем мут в секундах
MUTE_DURATION = 1209600

#telegram constants
ANONYMOUS_ADMIN_ID = '1087968824'
SERVICE_CHAT_ID = '777000'

#Логирование
logging.basicConfig(filename='Multibot.json', encoding='utf-8', level=logging.INFO,
                    format='%(levelname)s - %(asctime)s - %(name)s - %(message)s')

#Создаем словарь для замены латинских букв на кириллические
replacement_dict = {'e': 'е', 'y': 'у', 'u': 'и', 'o': 'о', 'p': 'р', 'a': 'а', 'k': 'к', 'x': 'х', 'c': 'с',
                    'n': 'п', 'm': 'т', 't': 'т', 'b': 'б', 'ё': 'е', '0':'о', 'ᴏ': 'о', '6':'б', '4':'ч', 'Ꭲ': 'т', 'ᴛ': 'т', 'Ꭼ': 'е', 'ᴇ': 'е',
                    'Ꮧ': 'л', 'Ꮯ': 'с', 'ᴄ': 'с', 'ɜ': 'з', 'ɯ': 'ш', 'ʙ': 'в', 'ᴧ': 'л', 'ᴨ': 'п', 'ᴩ': 'р', 'ᴋ': 'к', 'ᴀ': 'а'}
translation_table = str.maketrans(replacement_dict)

# Создаем список исключений
exclusions = ['geoscan', 'findprjbot']

#Функция для чтения ТОКЕНА и ID чатов из файла
def read_token_and_chat_id():
    try:
        with open(TOKEN_FILE, "r") as file:
            data = json.load(file)
            token = data.get("token")
            chat_ids = data.get("chat_id")
            owner_id = data.get("owner_id")
        #Проверяем, что данные были успешно считаны из файла
        if token is not None and chat_ids is not None:
            return token, chat_ids, owner_id
        else:
            log_error(f"Ошибка: Не удалось получить токен и/или ID чатов из файла '{TOKEN_FILE}'.")
            return None, None

    except FileNotFoundError:
        log_error(f"Файл '{TOKEN_FILE}' не найден.")
        return None, None

    except json.JSONDecodeError:
        log_error(f"Ошибка при чтении файла '{TOKEN_FILE}': неверный формат JSON.")
        return None, None

#Функция для записи данных в файл с указанием кодировки
def write_data_to_file(filename, data):
    with open(filename, "a", encoding="utf-8") as file:
        try:
            file.write(str(data) + "\n")
        except Exception as e:
            log_error(f"Ошибка при записи данных в файл: {e}")

#Функция для чтения данных из файла
def read_data_from_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = [line.strip().lower() for line in file]
    except FileNotFoundError:
        log_error(f"Файл '{filename}' не найден.")
        data = []
    return data

#Функция для записи события бана в файл
def record_ban_event(chat_name, user_id, user_name, message_text, phrase, event_type):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": current_time,
        "chat_name": chat_name,
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
            log_error(f"Ошибка при записи данных в файл: {e}")
    return BANSTAT_FILE

#Функция для записи попытки добавления бота
def record_bot_add_event(chat_name, user_id, user_name, bot_id, bot_name):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": current_time,
        "chat_name": chat_name,
        "user_id": user_id,
        "user_name": user_name,
        "bot_id": bot_id,
        "bot_name": bot_name}
    with open(BOT_STAT_FILE, "a", encoding="utf-8") as file:
        try:
            json.dump(entry, file, ensure_ascii=False)
            file.write("\n")
        except Exception as e:
            log_error(f"Ошибка при записи данных в файл: {e}")

#Чтение токена и ID чатов из файла
TOKEN, CHAT_IDS, OWNER_ID = read_token_and_chat_id()

#Создание объекта бота
bot = telebot.TeleBot(TOKEN)

#Устанавливаем параметр skip_bot для обработки сообщений от других ботов
bot.skip_pending = False

#ID бота
BOT_ID = bot.get_me().id

#Функция для получения информации об администраторах в каждом чате из списка CHAT_IDS
def get_chat_admins(chat_ids):
    admin_dict = {}
    for chat_id in chat_ids:
        admins = []
        try:
            chat_admins = bot.get_chat_administrators(chat_id)
            for admin in chat_admins:
                admins.append(str(admin.user.id))
        except Exception as e:
            print("Ошибка при получении администраторов чата:", e)
        admin_dict[chat_id] = admins
    return admin_dict

#Функция для удаления сообщения через 5 секунд
def delete_message_after_delay(chat_id, message_id, delay):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print("Не получилось удалить сообщение", e)

#Функция для очистки текста
def preprocess_text(text):
    #Удаляем все знаки препинания, спец символы и смайлики
    text = re.sub(r'[^\w\s]', '', text)
    #Заменяем множественные пробелы на одиночные
    text = re.sub(r'\s+', ' ', text)

    #Проходим по каждому слову в тексте
    words = text.split()
    result = []
    for word in words:
        #Проверяем, являются ли все символы в слове латинскими буквами
        if all(char.isalpha() and re.match('[a-z]', char.lower()) for char in word):
            #Если да, то оставляем слово без изменений
            result.append(word)
        else:
            #Иначе, производим замену символов
            result.append(word.translate(translation_table))
    return ' '.join(result)

#Функция подсчета сообщений в бане
def count_message_occurrences(text):
    count = 0
    #Проверяем, есть ли значение в кэше для данного сообщения
    if text in message_occurrences_cache:
        return message_occurrences_cache

    with open(BANSTAT_FILE, "r", encoding="utf-8") as file:
        for line in file:
            entry = json.loads(line)
            if entry.get("message_text") == text:
                count += 1
            if count >= message_count:
                #Сохраняем результат в кэше
                message_occurrences_cache[text] = count
                return message_occurrences_cache

#Логирование обращений к боту
def log_and_owner_message(notification_message):
    logging.info(notification_message.replace('\n', ' '))
    try:
        bot.send_message(OWNER_ID, notification_message)
        logging.info('Отправлено OWNER')
    except Exception as e:
        logging.error(f"Не удалось отправить OWNER {e}")

#Функция логирования и отправки сообщения админам
def log_and_admin_message(notification_message, chat_id):
    logging.info(notification_message.replace('\n', ' '))
    if OWNER_ID in admin_ids[chat_id]:
        for admin_id in admin_ids[chat_id]:
            if str(admin_id) == str(BOT_ID):
                continue
            try:
                bot.send_message(admin_id, notification_message)
                logging.info(f'Отправлено {admin_id}')
            except:
                pass
    else:
        try:
            bot.send_message(OWNER_ID, notification_message)
            logging.info('Отправлено OWNER')
        except Exception as e:
            logging.error(f"Не удалось отправить OWNER {e}")

        for admin_id in admin_ids[chat_id]:
            if str(admin_id) == str(BOT_ID):
                continue
            try:
                bot.send_message(admin_id, notification_message)
                logging.info(f'Отправлено {admin_id}')
            except:
                pass

#Логирование ошибок
def log_error(e):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Ошибка: {e}")
    logging.error(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Ошибка: {e}")
    #Пауза перед повторной попыткой
    time.sleep(10)

#Распознаём текст с картинки
def recognize_text(image_stream):
    #Открываем изображение с помощью PIL
    image = Image.open(image_stream)
    #Используем pytesseract для распознавания текста
    extracted_text = pytesseract.image_to_string(image, lang='rus')
    return extracted_text

#Чтение списка запрещенных фраз
banned_phrases = read_data_from_file(BANNED_PHRASES_FILE)
#banned_phrases_new = read_data_from_file(BANNED_PHRASES_FILE_NEW)

#Чтение списка фраз предупреждений
warning_phrases = read_data_from_file(WARNING_PHRASES_FILE)

#Создаем список для записи в файл
admin_ids = get_chat_admins(CHAT_IDS)
admin_values = [item for sublist in admin_ids.values() for item in sublist]

#Обработчик команды /start
@bot.message_handler(commands=["start", "help", "settings", "any_other_command"])
def handle_commands(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    message_text = message.text.strip()
    logging.info(f'{user_name} в чате {chat_id} написал /start')

#Проверка, что команда отправлена в личном сообщении и отправитель является администратором
    if str(user_id) in admin_values or str(user_id) == OWNER_ID:
        #Создаем клавиатуру
        keyboard = types.ReplyKeyboardMarkup(row_width=2)
        button_texts = ["Добавить данные в BAN", "Добавить данные в WARNING", "Статистика", "Статус"]
        for text in button_texts:
            button = types.KeyboardButton(text=text)
            keyboard.add(button)
        #Отправляем сообщение с клавиатурой в личное сообщение администратору
        try:
            bot.send_message(user_id, "Выберите действие:", reply_markup=keyboard, disable_notification = True)
        except ApiTelegramException as e:
            if e.error_code == 403:
                bot.send_message(chat_id, "Для работы с ботом, пожалуйста, разрешите получение сообщений от ботов в настройках конфиденциальности Telegram.", disable_notification = True)
            else:
                bot.send_message(chat_id, f"Произошла ошибка: {e}", disable_notification = True)
    else:
        try:
            bot.delete_message(chat_id, message.message_id)
            sent_message = bot.send_message(chat_id, 'У вас нет прав на такое действие')
            threading.Thread(target=delete_message_after_delay,
                             args=(sent_message.chat.id, sent_message.message_id, DELETE_MESSAGE_DELAY)).start()
        except Exception as e:
            log_error(f'Ошибка в обработке /start {e}')

#Обработчик для сообщений после выбора кнопки "Добавить данные в BAN"
@bot.message_handler(func=lambda message: message.text.strip() == "Добавить данные в BAN")
def add_to_ban_phrases(message):
    user_id = message.from_user.id

    if str(user_id) in admin_values or str(user_id) == OWNER_ID:
        bot.send_message(user_id, "Введите текст для добавления в BAN:", disable_notification = True)
        bot.delete_message(message.chat.id, message.message_id)
        bot.register_next_step_handler(message, process_ban_phrase, user_id)

#Функция для обработки текста, который нужно добавить в BAN
def process_ban_phrase(message, user_id):
    global banned_phrases
    notification_massege = []
    user_name = message.from_user.first_name
    lines = message.text.splitlines()

    for line in lines:
        new_phrase = preprocess_text(line)

    #Добавить новую фразу в файл Banned_phrases.json
        write_data_to_file(BANNED_PHRASES_FILE, new_phrase)
        logging.info(f'{user_id} {user_name} добавил фарзу "{new_phrase}" в BAN')
        notification_massege.append(new_phrase)

    #Отправить подтверждение администратору
    bot.send_message(user_id, f"Фраза\n{notification_massege}\nуспешно добавлена в BAN.", disable_notification = True)
    banned_phrases = read_data_from_file(BANNED_PHRASES_FILE)
    return banned_phrases

#Обработчик для сообщений после выбора кнопки "Добавить данные в WARNING"
@bot.message_handler(func=lambda message: message.text.strip() == "Добавить данные в WARNING")
def add_to_warning_phrases(message):
    user_id = message.from_user.id

    if str(user_id) in admin_values or str(user_id) == OWNER_ID:
        bot.send_message(user_id, "Введите текст для добавления в WARNING:", disable_notification = True)
        bot.delete_message(message.chat.id, message.message_id)
        bot.register_next_step_handler(message, process_warning_phrase, user_id)

#Функция для обработки текста, который нужно добавить в WARNING
def process_warning_phrase(message, user_id):
    global warning_phrases
    new_phrase = message.text.strip()
    user_name = message.from_user.first_name

    #Добавить новую фразу в файл warning_phrases.json
    write_data_to_file(WARNING_PHRASES_FILE, new_phrase)

    #Отправить подтверждение администратору
    bot.send_message(user_id, f"Фраза\n'{new_phrase}'\nуспешно добавлена в WARNING.", disable_notification = True)
    logging.info(f'{user_id} {user_name} добавил фарзу "{new_phrase}" в Warning')
    warning_phrases = read_data_from_file(WARNING_PHRASES_FILE)

    return warning_phrases

#Обработчик для сообщений после выбора кнопки "Статистика"
@bot.message_handler(func=lambda message: message.text.strip() == "Статистика")
def handle_statistics(message):
    user_id = message.from_user.id
    if str(user_id) in admin_values or str(user_id) == OWNER_ID:
        bot.send_message(user_id,"Введите интервал дат для вывода статистики в формате 'гггг-мм-дд гггг-мм-дд', например, '2024-02-01 2024-02-07':", disable_notification = True)
        bot.delete_message(message.chat.id, message.message_id)
        bot.register_next_step_handler(message, process_dates)

#Функция для обработки полученных дат
def process_dates(message):
    date_range = message.text.split()
    chat_id = message.chat.id
    if len(date_range) == 1:
        start_date = end_date = date_range[0]
    elif len(date_range) == 2:
        start_date, end_date = date_range
    else:
        bot.send_message(chat_id, "Неправильный формат ввода. Попробуйте снова.", disable_notification = True)
        return

    file_path = BANSTAT_FILE
    file_bot_path = BOT_STAT_FILE
    count_ban, count_warning, count_bot, count_mut, count_chn = count_events(file_path, file_bot_path, start_date, end_date)
    count_sum = count_chn + count_bot + count_mut + count_ban + count_warning
    bot.send_message(chat_id, f"За период с {start_date} по {end_date}:\n"
                                      f"Всего подозрительных {count_sum}, из них:\n"
                                      f"Рекламных {count_ban} сообщений;\n"
                                      f"Вынесено {count_warning} предупреждений;\n"
                                      f"Попыток рекламмы каналов {count_chn};\n"
                                      f"Заблокировано {count_mut};\n"
                                      f"Удалено {count_bot} ботов", disable_notification = True)

#Функция для подсчета событий в указанном диапазоне дат
def count_events(file_path, file_bot_path, start_date, end_date):
    count_ban = 0
    count_warning = 0
    count_bot = 0
    count_mut = 0
    count_chn = 0
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
                elif event_data['event_type'] == 'CHN':
                    count_chn +=1
    with open(file_bot_path, 'r', encoding='utf-8') as file:
        for line in file:
            event_data = json.loads(line)
            timestamp = datetime.strptime(event_data['timestamp'][:10], '%Y-%m-%d')
            if start_datetime <= timestamp <= end_datetime:
                count_bot += 1
    return count_ban, count_warning, count_bot, count_mut, count_chn

#Обработчик для сообщений после выбора кнопки "Статус"
@bot.message_handler(func=lambda message: message.text.strip() == "Статус")
def status_command(message):
    user_id = message.from_user.id

    if str(user_id) in admin_values or str(user_id) == OWNER_ID:
        #Отправляем сообщение со статусом и временем запуска бота
        bot.send_message(user_id, f"Статус бота: онлайн\nВремя запуска бота: {bot_start_time}", disable_notification = True)
        bot.delete_message(message.chat.id, message.message_id)

#Обработка сообщений с фото
@bot.message_handler(content_types=['photo', 'audio', 'documents', 'video', 'voice', 'sticker'])
def handle_photo(message):
    user_id = message.from_user.id
    #Не выполняем никаких действий
    if str(user_id) in admin_values or str(user_id) in {OWNER_ID, ANONYMOUS_ADMIN_ID, SERVICE_CHAT_ID}:
        return

    #Обработка подписи к фотографии, если есть
    message_text = str()
    if message.caption:
        message_text = message.caption
    if message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        with requests.get(file_url) as response:
            image_stream = BytesIO(response.content)
            # Распознаем текст на картинке
            extracted_text = recognize_text(image_stream)
            message_text += f" Текст с картинки: '{extracted_text}'"
            handle_text_messages(message, message_text)

#Обработка всех текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message, message_text=None):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    chat_id = message.chat.id
    chat_title = bot.get_chat(chat_id).title
    if chat_title is None:
        chat_title = 'Лично'
    message_id = message.message_id
    words = ()

    #Проверка, является ли отправитель администратором, владельцем или сообщение от имени группы
    #Не выполняем никаких действий
    if str(user_id) in admin_values or str(user_id) in {OWNER_ID, ANONYMOUS_ADMIN_ID, SERVICE_CHAT_ID}:
        return

    #Если нет текста не выполняем дальше
    if message_text is None:
        message_text = message.text
        if message_text is None:
            return

    #Логируем сообщение для возможности разбора
    logging.info(f"({user_id}; {user_name}; {chat_title}), {message_text.replace('\n', ' ')}")

    #Приводим текст в единый формат
    text = preprocess_text(message_text)

    #Попытка отправить команду
    if message_text.startswith('/') and " " not in message_text:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            log_error(f"Ошибка при попытке удалить команду от {user_id} в чате '{chat_title}/{chat_id}': {e}")

        notification_message = f"Пользователь {user_name} (ID: {user_id}) В чате '{chat_title}/{chat_id}'\nпопробовал отправить команду:\n'{message_text.replace('\n', ' ')}'\nсообщение удалено"
        log_and_owner_message(notification_message)
        return

    #Проверка на повторяющиеся сообщения
    if count_message_occurrences(message_text):
        bot.delete_message(chat_id, message_id)
        notification_message = f"Пользователь {user_name} (ID: {user_id}) В чате '{chat_title}'\nотправил повторяющееся сообщение:\n'{message_text.replace('\n', ' ')}'\nя его замутил на 14 дней"
        record_ban_event(chat_title, user_id, user_name, message_text, 'повтор сообщения', "MUT")
        log_and_admin_message(notification_message, chat_id)
        #bot.kick_chat_member(CHAT_ID, user_id)
        try:
            bot.restrict_chat_member(chat_id, user_id, until_date=time.time() + MUTE_DURATION, can_send_messages=False)
            logging.info(f"Пользователь {user_name} ID: {user_id} в чате '{chat_title}', заблокирован на 14 дней")
        except Exception as e:
            log_error(f"Ошибка при попытке заблокировать пользователя {user_id} в чате '{chat_title}': {e}")
        return

    #Проверяем наличие каналов в сообщении
    if re.search(r'(?<!\w)@(?!' + '|'.join(exclusions) + r')\w+', message_text, re.I):
        bot.delete_message(chat_id, message_id)
        notification_message = f"Пользователь {user_name} (ID: {user_id}) В чате '{chat_title}'\nпопробовал рекламировать канал:\n'{message_text.replace('\n', ' ')}'\nсообщение удалено"
        log_and_admin_message(notification_message, chat_id)
        record_ban_event(chat_title, user_id, user_name, message_text, "КАНАЛ", "CHN")
        ban_message = f"Я подозреваю, что {user_name} (ID: {user_id}) отправил приглашение в сомнительный канал, этому сообщению не место в этом чате!"
        sent_message = bot.send_message(chat_id, ban_message, disable_notification=True)
        threading.Thread(target=delete_message_after_delay,
                         args=(sent_message.chat.id, sent_message.message_id, DELETE_MESSAGE_DELAY)).start()
        return

    #Проверка на наличие рекламных сообщений
    for phrase in banned_phrases:
        words = phrase.split()
        found = all(word.lower() in text.lower() for word in words)
        if found:
            ban_message = f"Я подозреваю, что {user_name} (ID: {user_id}) отправил рекламу, этому сообщению не место в этом чате!"
            bot.delete_message(chat_id, message_id)
            record_ban_event(chat_title, user_id, user_name, message_text, phrase, "BAN")
            sent_message = bot.send_message(chat_id, ban_message, disable_notification = True)
            notification_message = f"Сообщение от пользователя {user_name} (ID: {user_id}) удалено из чата '{chat_title}' за отправку рекламы\nСловосочетание:\n'{phrase}'\nСообщение пользователя:\n'{message_text.replace('\n', ' ')}'"
            log_and_admin_message(notification_message, chat_id)
            threading.Thread(target=delete_message_after_delay,
                             args=(sent_message.chat.id, sent_message.message_id, DELETE_MESSAGE_DELAY)).start()
            break

    #Проверка на наличие матерных слов
    if not found:
        for phrase in warning_phrases:
            words = phrase.split()
            found = any(len(word) == len(word.lower()) and word.lower() in text.split() for word in words)
            if found:
                warning_message = f"Пользователь {user_name} (ID: {user_id}) ваше сообщение содержало запрещенное в этом чате слово {phrase}, попробуйте написать иначе."
                bot.delete_message(chat_id, message_id)
                record_ban_event(chat_title, user_id, user_name, message_text, phrase, "WARNING")
                sent_message = bot.send_message(chat_id, warning_message, disable_notification = True)
                notification_message = f"Сообщение от пользователя  {user_name} (ID: {user_id}) удалено из чата '{chat_title}' за отправку сообщения с матом:\nСлово:\n{phrase}\nСообщение пользователя:\n'{message_text.replace('\n', ' ')}'"
                log_and_admin_message(notification_message, chat_id)
                threading.Thread(target=delete_message_after_delay,
                                 args=(sent_message.chat.id, sent_message.message_id, DELETE_MESSAGE_DELAY)).start()
                break

#Удаление сообщений о вступлении и выходе из чата
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member', 'new_chat_title', 'new_chat_photo',
                                    'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created',
                                    'channel_chat_created', 'migrate_to_chat_id', 'migrate_from_chat_id'])
def delete(message):
    try:
        if message.content_type == 'new_chat_members':
            for new_chat_member in message.new_chat_members:
                if new_chat_member.is_bot:
                    #Попытка выгнать бота из чата
                    bot.kick_chat_member(message.chat.id, new_chat_member.id)
                    #Получение информации о пользователе, попытка записи события
                    chat_title = bot.get_chat(chat_id).title
                    user_id = message.from_user.id
                    user_name = message.from_user.first_name + ' ' + message.from_user.last_name
                    bot_id = new_chat_member.id
                    bot_name = new_chat_member.username
                    record_bot_add_event(chat_title, user_id, user_name, bot_id, bot_name)
                    notification_message = f"Пользователь {user_name} (ID: {user_id}) попытался добавить бота:\n'{bot_name}'\nв чат '{chat_title}'"
                    log_and_admin_message(notification_message, chat_id)
        #Попытка удалить сообщение
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        #Обработка ошибок
        log_error(f"Произошла ошибка при удалении информационного сообщения: {e}")

#Запуск бота
while True:
    try:
        bot_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        admins_info = get_chat_admins(CHAT_IDS)
        for chat_id, admins_list in admins_info.items():
            chat_title = bot.get_chat(chat_id).title
            print(f"Бот запущен в {bot_start_time} в чате '{chat_title}'")
            logging.info(f"Бот запущен в {bot_start_time} в чате ID {chat_id}, {chat_title}")
            #Получение данных администраторов в чате
            admins_list_details = []
            admin_id = None
            for admin_id in admins_list:
                try:
                    admin_info = bot.get_chat_member(chat_id, user_id=int(admin_id))
                    admin_name = admin_info.user.first_name
                    admin_last_name = admin_info.user.last_name if admin_info.user.last_name else ''
                    admins_list_details.append(admin_name + ' ' + admin_last_name)
                except Exception as e:
                    print(f"Ошибка при получении данных администратора {admin_id} в чате '{chat_title}': {e}")
            print(f'Администраторы {admins_list_details}\n ')
            logging.info(f'Администраторы {admins_list_details}')
        bot.polling(timeout=320, none_stop=True)
        #Задержка перед повторным опросом
        time.sleep(5)

#Обработка ошибок
    except telebot.apihelper.ApiTelegramException as e:
        log_error(f'Ошибка после запуска 1 {e}')
        continue
    except Exception as e:
        log_error(f'Ошибка после запуска 2 {e}')
        continue
    except socket.gaierror as e:
        log_error(f'Ошибка соединения: {e}')
        time.sleep(10)  # Пауза перед повторной попыткой
        continue
