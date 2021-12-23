from configparser import ConfigParser
import os


def read_config():
    conn = ConfigParser()
    file_path = os.path.join(os.path.abspath('.'), 'config.ini')
    if not os.path.exists(file_path):
        return ""

    conn.read(file_path)
    token = conn.get("userInfo", "token")
    return token
