import os
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

DROP_PCT = float(os.getenv("DROP_PCT", -20))
RSI_THRESHOLD = float(os.getenv("RSI_THRESHOLD", 40))
WINDOW_HIGHEST_DAYS = int(os.getenv("WINDOW_HIGHEST_DAYS", 60))
MIN_BARS = int(os.getenv("MIN_BARS", 60))

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
MAIL_TO = os.getenv("MAIL_TO")

EMAIL_ENABLED = all([SMTP_HOST, SMTP_USER, SMTP_PASS, MAIL_TO])
