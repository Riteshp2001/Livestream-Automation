import os
import json
from dotenv import load_dotenv

load_dotenv()

PIXABAY_API_KEY = os.environ.get('PIXABAY_API_KEY')
FREESOUND_API_KEY = os.environ.get('FREESOUND_API_KEY')
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]
USED_CONTENT_FILE = 'data/used_content.json'

def load_config():
    with open('data/auto.json', 'r') as f:
        return json.load(f)
