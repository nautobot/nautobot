from dotenv import load_dotenv
from mypy_django_plugin import main
import nautobot


def plugin(version):
    load_dotenv("development/dev.env")
    nautobot.setup()
    return main.plugin(version)
