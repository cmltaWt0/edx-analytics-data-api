"""Test settings and globals."""



from analyticsdataserver.settings.base import *

########## IN-MEMORY TEST DATABASE
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
}

# Silence elasticsearch during tests
LOGGING['loggers']['elasticsearch']['handlers'] = ['null']

LMS_BASE_URL = 'http://lms-host'

LMS_USER_ACCOUNT_BASE_URL = 'http://lms-host'

# Default elasticsearch port when running locally
ELASTICSEARCH_LEARNERS_HOST = environ.get("ELASTICSEARCH_LEARNERS_HOST", 'http://localhost:9223/')
ELASTICSEARCH_LEARNERS_INDEX = 'roster_test_001'
ELASTICSEARCH_LEARNERS_INDEX_ALIAS = 'roster_test'
ELASTICSEARCH_LEARNERS_UPDATE_INDEX = 'index_update_test'

# Default the django-storage settings so we can test easily
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = 'xxxxx'
AWS_SECRET_ACCESS_KEY = 'xxxxx'
AWS_STORAGE_BUCKET_NAME = 'fake-bucket'
AWS_DEFAULT_ACL = None
FTP_STORAGE_LOCATION = 'ftp://localhost:80/path'

# Default settings for report download endpoint
COURSE_REPORT_FILE_LOCATION_TEMPLATE = '/{course_id}_{report_name}.csv'
COURSE_REPORT_DOWNLOAD_EXPIRY_TIME = 120
