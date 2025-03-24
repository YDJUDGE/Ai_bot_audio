import hashlib
import json
import os
import logging
import telebot
from config_bot import bot_token
from audio_processor import AudioProcess
from my_proof.proof import Proof

# Настройки логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем токен
TOKEN = bot_token
bot = telebot.TeleBot(TOKEN)

# Папка для хранения аудиофайлов
AUDIO_DIR = "data/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)  # Создаём директорию для аудио файлов, если она существует

PROCESSED_FILES_PATH = "data/processed_files.json"

if os.path.exists(PROCESSED_FILES_PATH):
    with open(PROCESSED_FILES_PATH, "r") as f:
        processed_files = json.load(f)
else:
    processed_files = {}
    processed_messages = set()

proof_instance = Proof()

def save_processed_files():
    """Сохраняет processed_files в файл"""
    with open(PROCESSED_FILES_PATH, "w") as f:
        json.dump(processed_files, f)

def save_audio(file_id, file_ext, message_id):
    """Сохраняет аудиофайл и возвращает путь"""
    logger.info(f"Сохранение аудио: file_id={file_id}, message_id={message_id}")

    file_info = bot.get_file(file_id)
    file_path = file_info.file_path
    downloaded_file = bot.download_file(file_path)

    file_hash = hashlib.md5(downloaded_file).hexdigest()

    if file_hash in processed_files:
        logger.info(f"Файл с хэшом {file_hash} уже обработан, статус: {processed_files[file_hash]}, пропускаем сохранение")
        return None, file_hash

    original_file = os.path.join(AUDIO_DIR, f"{file_id}{file_ext}")
    wav_file = os.path.join(AUDIO_DIR, f"{file_id}.wav")

    os.makedirs(AUDIO_DIR, exist_ok=True)

    with open(original_file, "wb") as f:
        f.write(downloaded_file)

    logger.info(f"Файл сохранён: {original_file}")

    # Конвератция в wav
    AudioProcess.convert_to_wav(original_file, wav_file)

    if os.path.exists(original_file):
        os.remove(original_file)
        logger.info(f"Оригинальный файл удалён: {original_file}")

    return wav_file, file_hash

@bot.message_handler(content_types=["audio", "voice"])
def handle_audio(message):
    """Обрабатывает входящие аудиофайлы"""
    logger.info(f"Обработка сообщения: message_id={message.message_id}")

    if message.message_id in processed_messages:
        logger.info(f"Сообщение {message.message_id} уже обработано, пропускаем")
        return
    processed_messages.add(message.message_id)

    try:
        if message.audio:
            file_id = message.audio.file_id
            file_ext = ".mp3"  # Телеграмм хранит аудио в mp3
        elif message.voice:
            file_id = message.voice.file_id
            file_ext = ".ogg"  # Для голосовых сообщений
        else:
            bot.reply_to(message, "Неверный формат файла, отправьте голосовое или аудио сообщение")
            return

        audio_path, file_hash = save_audio(file_id, file_ext, message.message_id)
        if audio_path is None:
            status = processed_files[file_hash]["status"]
            if status == "low_quality":
                bot.reply_to(message, "Этот файл уже был отправлен ранее, но был откланён из-за низкого качества")
            else:
                bot.reply_to(message, "Этот аудио файл уже был обработан ранее. Повторная обработка не допускается")
            return

        bot.reply_to(message, "Аудио файл сохранён")

        # Вызов обработки
        processor = AudioProcess()
        uniqueness, features = processor.process_audio(audio_path)
        logger.info(f"Аудио сохранено: {audio_path}, уникальность: {uniqueness:.2f}")

        proof_result = proof_instance.generate([audio_path])
        logger.info(f"Proof создан: {proof_result}")

        # Проверяем качество
        if proof_result.quality <= 0.5:
            logger.info(f"Качество аудио слишком низкое ({proof_result.quality:.2f}), удаляем файлы")
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Файл удалён из-за низкого качества: {audio_path}")
            bot.reply_to(message, "Качество аудио слишком низкое (меньше или равно 0.5), файл не сохранён")
            return

        # Сохраняем признаки для будущих сравнений
        processor.processed_features.append(features)

        # Добавим в хэш обработанные аудио со статусом processed
        processed_files[file_hash] = {"status": "processed", "file_ids": [file_id]}
        save_processed_files()

        # Рассчитываем сумму выплаты
        payout = proof_result.score * 100


        bot.reply_to(message,
                     f"Обработанное аудио:\n"
                     f"Валидность: {"Да" if proof_result.valid else "Нет"}\n"
                     f"Уникальность: {uniqueness:.2f}\n"
                     f"Качество: {proof_result.quality:.2f}\n"
                     f"Сумма выплаты: {payout:.2f} усл. ед"
                     )

    except Exception as e:
        logger.error(f"Ошибка при обработке: {e}")
        bot.reply_to(message, "Произошла ошибка при обработке аудио файла")

if __name__ == "__main__":
    logger.info("Бот запущен")
    bot.polling(non_stop=True)
