import os
import logging
import requests
import vk_api
import telegram
from dotenv import load_dotenv
import service_functions
import glob


VERSION_VKONTAKTE = '5.52'
logger = logging.getLogger('posting')


def upload_photo_to_vk(vk_session, params, filename):
    uploader = vk_api.VkUpload(vk_session)
    photo_to_post = uploader.photo(
        filename,
        album_id=params['vk_album_id'],
        group_id=params['vk_group_id']
    )
    return photo_to_post


def upload_photo_to_facebook(params, filename):
    url = 'https://graph.facebook.com/v7.0/{0}/photos'.format(params['facebook_group_id'])
    with open(filename, 'rb') as file_handler:
        files = {
            'source': file_handler
        }
        facebook_params = {
            'access_token': params['access_token'],
            'published': False,
        }
        dict_data = service_functions.query_to_site(url, facebook_params, files)
        if dict_data:
            return dict_data['id']


def post_vkontakte(params, message, images):
    vk_session = vk_api.VkApi(token=params['vk_access_token'])
    vk = vk_session.get_api()
    photos_to_post = [upload_photo_to_vk(vk_session, params, image) for image in images if images]
    attachments = [service_functions.get_attachment(photo_to_post) for photo_to_post in photos_to_post if photos_to_post]
    vk.wall.post(
        owner_id=-params['vk_group_id'],
        attachments=','.join(attachments),
        message=message
    )


def post_telegram(params, message, images):
    proxy = telegram.utils.request.Request(proxy_url=os.environ.get('PROXY'))
    telegram_bot = telegram.Bot(token=params['telegram_access_token'], request=proxy)
    for image in images:
        with open(image, 'rb') as file_handler:
            telegram_bot.sendPhoto(chat_id=params['telegram_chat_id'], photo=file_handler)
    telegram_bot.sendMessage(chat_id=params['telegram_chat_id'], text=message)


def post_facebook(params, message, images):
    url = 'https://graph.facebook.com/v7.0/{0}/feed'.format(params['facebook_group_id'])
    facebook_params = {
        'access_token': params['facebook_access_token'],
        'facebook_group_id': params['facebook_group_id'],
        'message': message
    }
    photo_ids = [upload_photo_to_facebook(facebook_params, image) for image in images if images]
    attachments = ["{'media_fbid':'%s'}" % str(photo_id) for photo_id in photo_ids if photo_ids]
    if not attachments:
        raise ValueError('Отсутствуют изображения! Публикация в facebook не выполнена!')
    facebook_params['attached_media'] = '[%s]' % ','.join(attachments)

    service_functions.query_to_site(url, facebook_params)


def initialize_logger():
    output_dir = os.path.dirname(os.path.realpath(__file__))
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(os.path.join(output_dir, 'log.txt'), "a")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def post_on_social_media(posting_function, params, message, images, title_of_site):
    try:
        posting_function(params, message, images)
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
        logger.info('Публикация поста {0} успешно завершена'.format(title_of_site))


def main():

    load_dotenv()
    initialize_logger()

    params = {
        'vk_access_token': os.environ.get('VK_ACCESS_TOKEN'),
        'telegram_access_token': os.environ.get('TELEGRAM_ACCESS_TOKEN'),
        'facebook_access_token': os.environ.get('FACEBOOK_ACCESS_TOKEN'),
        'vk_group_id': int(os.environ.get('VK_GROUP_ID')),
        'vk_album_id': int(os.environ.get('VK_ALBUM_ID')),
        'telegram_chat_id': os.environ.get('TELEGRAM_CHAT_ID'),
        'facebook_group_id': os.environ.get('FACEBOOK_GROUP_ID'),
        'v': VERSION_VKONTAKTE
    }

    message = service_functions.get_message()
    images = glob.glob('images/*.*')

    post_on_social_media(post_vkontakte, params, message, images, 'vk')
    post_on_social_media(post_telegram, params, message, images, 'telegram')
    post_on_social_media(post_facebook, params, message, images, 'facebook')


if __name__ == '__main__':
    main()
