import os
import logging
import argparse
import requests
import vk_api
import telegram
from dotenv import load_dotenv
import service_functions
import glob


logger = logging.getLogger('posting')


def upload_photo_to_vk(vk_session, vk_group_id, vk_album_id, filename):
    uploader = vk_api.VkUpload(vk_session)
    photo_to_post = uploader.photo(
        filename,
        album_id=vk_album_id,
        group_id=vk_group_id
    )
    return photo_to_post


def upload_photo_to_facebook(fb_token, fb_group_id, filename):
    url = 'https://graph.facebook.com/v7.0/{0}/photos'.format(fb_group_id)
    with open(filename, 'rb') as file_handler:
        files = {
            'source': file_handler
        }
        facebook_params = {
            'access_token': fb_token,
            'published': False,
        }
        dict_data = service_functions.query_to_site(url, facebook_params, files)
        if dict_data:
            return dict_data['id']


def post_vkontakte(vk_token, vk_group_id, vk_album_id, message, images):
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()
    photos_to_post = [upload_photo_to_vk(vk_session, vk_group_id, vk_album_id, image) for image in images if images]
    attachments = [service_functions.get_attachment(photo_to_post) for photo_to_post in photos_to_post if photos_to_post]
    vk.wall.post(
        owner_id=-vk_group_id,
        attachments=','.join(attachments),
        message=message
    )


def post_telegram(telegram_token, telegram_chat_id, message, images):
    proxy = telegram.utils.request.Request(proxy_url=os.environ.get('TELEGRAM_PROXIES'))
    telegram_bot = telegram.Bot(token=telegram_token, request=proxy)
    for image in images:
        with open(image, 'rb') as file_handler:
            telegram_bot.sendPhoto(chat_id=telegram_chat_id, photo=file_handler)
    telegram_bot.sendMessage(chat_id=telegram_chat_id, text=message)


def post_facebook(fb_token, fb_group_id, message, images):
    url = 'https://graph.facebook.com/v7.0/{0}/feed'.format(fb_group_id)
    fb_params = {
        'access_token': fb_token,
        'facebook_group_id': fb_group_id,
        'message': message
    }
    photo_ids = [upload_photo_to_facebook(fb_token, fb_group_id, image) for image in images if images]
    attachments = ["{'media_fbid':'%s'}" % str(photo_id) for photo_id in photo_ids if photo_ids]
    if images and not attachments:
        raise ValueError('Ошибка загрузки изображений! Публикация в facebook не выполнена!')
    fb_params['attached_media'] = '[%s]' % ','.join(attachments)

    service_functions.query_to_site(url, fb_params)


def post_on_social_media(posting_function, message, images, **kwargs):
    try:
        if 'album_id' in kwargs:
            posting_function(kwargs['token'], kwargs['id'], kwargs['album_id'], message, images)
        else:
            posting_function(kwargs['token'], kwargs['id'], message, images)

    except (vk_api.VkApiError, vk_api.ApiHttpError, vk_api.AuthError) as error:
        logger.error('Ошибка публикации поста на сайт вконтакте: {0}'.format(error))

    except telegram.TelegramError as error:
        logger.error('Ошибка публикации поста в телеграмме: {0}'.format(error))

    except requests.exceptions.HTTPError as error:
        logger.error('Ошибка загрузки данных на сайт: {0}'.format(error))

    except (KeyError, TypeError) as error:
        logger.error('Ошибка загрузки или публикации поста: {0}'.format(error))

    except ValueError as error:
        logger.error(f'{error}')

    except OSError as error:
        logger.error('Ошибка чтения файлов с содержимым поста: {0}'.format(error))

    else:
        logger.info('Публикация поста {0} успешно завершена'.format(kwargs['title']))


def create_parser():
    parser = argparse.ArgumentParser(description='Параметры запуска скрипта')
    parser.add_argument('-f', '--file', default='message.txt', help='Текстовый файл с содержанием публикуемого поста')
    parser.add_argument('-i', '--images', default='images', help='Путь к каталогу с картинками для публикации')
    parser.add_argument('-l', '--log', help='Путь к каталогу с log файлом')
    return parser


def initialize_logger(log_path):
    if log_path:
        output_dir = log_path
    else:
        output_dir = os.path.dirname(os.path.realpath(__file__))
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(os.path.join(output_dir, 'log.txt'), "a")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main():

    load_dotenv()
    parser = create_parser()
    args = parser.parse_args()
    initialize_logger(args.log)

    message = service_functions.get_message(args.file)
    images = glob.glob(f'{args.images}/*.*')

    post_on_social_media(post_vkontakte, message, images,
                         token=os.getenv('VK_ACCESS_TOKEN'),
                         id=int(os.getenv('VK_GROUP_ID')),
                         album_id=int(os.getenv('VK_ALBUM_ID')),
                         title='vc')
    post_on_social_media(post_telegram, message, images,
                         token=os.getenv('TELEGRAM_ACCESS_TOKEN'),
                         id=os.getenv('TELEGRAM_CHAT_ID'),
                         title='telegram')
    post_on_social_media(post_facebook, message, images,
                         token=os.getenv('FACEBOOK_ACCESS_TOKEN'),
                         id=os.getenv('FACEBOOK_GROUP_ID'),
                         title='facebook')


if __name__ == '__main__':
    main()
