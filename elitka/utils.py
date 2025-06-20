from datetime import datetime

def get_time():
    format = '%M'
    return datetime.now().strftime(format)