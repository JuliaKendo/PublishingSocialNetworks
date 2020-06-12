import requests


def get_message(filename):
    with open(filename, "r") as file_handler:
        return file_handler.read()


def get_attachment(photo_to_post):
    attachment = ''
    if photo_to_post:
        attachment = 'photo{0}_{1}'.format(photo_to_post[0]['owner_id'], photo_to_post[0]['id'])
    return attachment


def query_to_site(url, params, files=None):
    response = requests.post(url, data=params, files=files or {})
    response.raise_for_status()
    return response.json()
