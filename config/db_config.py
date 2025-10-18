from decouple import config
import os


USE_REMOTE_DB = os.getenv("USE_REMOTE_DB", "false").lower() == "true"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        **({'OPTIONS': {'sslmode': 'require'}} if USE_REMOTE_DB else {}),
    }
}
