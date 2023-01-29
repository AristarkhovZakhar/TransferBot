import telebot
from telebot import types
from model import *
from mytoken import token_name
import requests
import logging

logging.basicConfig(level=logging.INFO, filename="bot_log.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")

bot = telebot.TeleBot(token_name)
# API   для рандомных фото
url = "https://picsum.photos/200/300?random=2"
# по умолчанию режим с двумя фото
mode = 1


# получение фото и гифки из модели
def image_with_style(content_image, style_image):
    content = image_loader(content_image)
    style = image_loader(style_image)
    input = content.clone()
    try:
        output_image, Images = run_style_transfer(cnn, cnn_norm_mean, cnn_norm_std,
                                                  content, style, input)
    except Exception:
        logging.error(f"Ошибка в обучении модели___{Exception}")
    image = unloader(output_image.squeeze(0))
    return image, Images


# отправка гифки
def send_gif(message):
    img = open('gif.gif', 'rb')
    bot.send_video(message.chat.id, img)
    img.close()


# делаем три кнопки
def make_main_bottom():
    markup = types.ReplyKeyboardMarkup()
    pair_photo = types.KeyboardButton('Скину две фотографии,первая'
                                      ' - контент, со второй взять стиль')
    one_content_photo = types.KeyboardButton('Скину одну фотографию, '
                                             'применить к ней стиль рандомной фотографии')
    one_style_photo = types.KeyboardButton('Применить стиль моей фотографии к рандомной фотографии')
    markup.add(pair_photo, one_content_photo, one_style_photo)
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    mess = f'Привет, <b>{message.from_user.first_name}</b>, ' \
           f'я могу переносить стиль с одной фотографии на другую.' \
           f' Можешь посмотреть как интересно получается.'
    bot.send_message(message.chat.id, mess, parse_mode='html')
    send_gif(message)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    pair_photo = types.KeyboardButton('Скину две фотографии,первая'
                                      ' - контент, со второй взять стиль')
    one_content_photo = types.KeyboardButton('Скину одну фотографию, '
                                             'применить к ней стиль рандомной фотографии')
    one_style_photo = types.KeyboardButton('Применить стиль моей фотографии к рандомной фотографии')
    markup.add(pair_photo, one_content_photo, one_style_photo)
    bot.send_message(message.chat.id, 'Понравилось?', reply_markup=markup)


@bot.message_handler()
def get_text(message):
    global mode
    if message.text == 'Скину две фотографии,первая - контент, со второй взять стиль':
        mode = 1
        bot.send_message(message.chat.id, 'Ждем отправки фотографии контента')
    elif message.text == 'Скину одну фотографию, применить к ней стиль рандомной фотографии':
        mode = 2
        bot.send_message(message.chat.id, 'Ждем отправки фотографии контента')
    elif message.text == 'Применить стиль моей фотографии к рандомной фотографии':
        mode = 3
        bot.send_message(message.chat.id, 'Ждем отправки фотографии стиля')


photo_num = 0


@bot.message_handler(content_types=['photo'])
def get_photo(message):
    global photo_num
    if mode == 1 and photo_num == 0:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f'{photo_num}.jpg', 'wb') as new_file:
            new_file.write(downloaded_file)
        logging.info("Изображение контента загружено")
        bot.send_message(message.chat.id, 'Ждем отправки фотографии стиля')
        photo_num += 1
    elif mode == 1 and photo_num == 1:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f'{photo_num}.jpg', 'wb') as new_file:
            new_file.write(downloaded_file)
        logging.info("Изображение стиля загружено")
        bot.send_message(message.chat.id, 'Наичнаем процесс обучения, это займет около 3-х минут')
        logging.info("Начало обучения")
        image, Images = image_with_style("0.jpg", "1.jpg")
        bot.send_photo(message.chat.id, image)
        make_gif(Images)
        img = open('1.gif', 'rb')
        bot.send_video(message.chat.id, img)
        img.close()
        logging.info("Успешно")
        photo_num = 0

    if mode == 2:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f'{photo_num}.jpg', 'wb') as new_file:
            new_file.write(downloaded_file)
        logging.info("Изображение контента загружено")
        photo_num += 1
        bot.send_message(message.chat.id, 'Отправляем рандомное фото, стиль которого будет применен')
        response = requests.get(url)
        with open("1.jpg", 'wb') as f:
            f.write(response.content)
        logging.info("Изображение стиля загружено")
        bot.send_photo(message.chat.id, open("1.jpg", 'rb'))
        content = image_loader("0.jpg")
        style = image_loader("1.jpg")
        input = content.clone()
        bot.send_message(message.chat.id, 'Наичнаем процесс обучения, это займет около 3-х минут')
        logging.info("Начало обучения")
        try:
            output_image, Images = run_style_transfer(cnn, cnn_norm_mean, cnn_norm_std,
                                                      content, style, input)
        except Exception:
            logging.error(f"Ошибка в обучении модели___{Exception}")

        image = unloader(output_image.squeeze(0))
        make_gif(Images)
        img = open('1.gif', 'rb')
        bot.send_video(message.chat.id, img)
        img.close()
        bot.send_photo(message.chat.id, image)
        logging.info("Успешно")
        photo_num = 0

    if mode == 3:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f'{photo_num}.jpg', 'wb') as new_file:
            new_file.write(downloaded_file)
        logging.info("Изображение стиля загружено")
        photo_num += 1
        bot.send_message(message.chat.id, 'Отправляем рандомное фото,'
                                          'к которому будет применен стиль вашего фото')
        response = requests.get(url)
        with open("1.jpg", 'wb') as f:
            f.write(response.content)
        logging.info("Изображение контента загружено")
        bot.send_photo(message.chat.id, open("1.jpg", 'rb'))
        content = image_loader("1.jpg")
        style = image_loader("0.jpg")
        input = content.clone()
        bot.send_message(message.chat.id, 'Наичнаем процесс обучения, это займет около 3-х минут')
        logging.info("Начало обучения")
        try:
            output_image, Images = run_style_transfer(cnn, cnn_norm_mean, cnn_norm_std,
                                                      content, style, input)
        except Exception:
            logging.error(f"Ошибка в обучении модели___{Exception}")

        image = unloader(output_image.squeeze(0))
        make_gif(Images)
        gif = open('1.gif', 'rb')
        bot.send_video(message.chat.id, gif)
        bot.send_photo(message.chat.id, image)
        gif.close()
        logging.info("Успешно")
        photo_num = 0


bot.polling(none_stop=True)
