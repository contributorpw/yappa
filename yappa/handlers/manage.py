import io
import logging
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from yappa.settings import DEFAULT_CONFIG_FILENAME
from yappa.utils import load_yaml

logger = logging.getLogger(__name__)

try:
    config = load_yaml(
            Path(Path(__file__).resolve().parent.parent,
                 DEFAULT_CONFIG_FILENAME))
    os.environ["DJANGO_SETTINGS_MODULE"] = config["DJANGO_SETTINGS_MODULE"]
except KeyError:
    logger.error("DJANGO_SETTINGS_MODULE not present in the config")
except ValueError:
    logger.warning("Couldn't load app. Looks like broken Yappa config is used")

FORBIDDEN_COMMANDS = (
        'dbshell',
        'makemigrations',
        'runserver',
        'shell',
        'squashmigrations',
        'startapp',
        'startproject',
        )

NOINPUT_COMMANDS = (
        "createsuperuser",
        "migrate",
        )


def run_command(command, args):
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
                ) from exc
    with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
        try:
            if not {"--noinput", "--no-input"}.intersection(args) \
                    and command in NOINPUT_COMMANDS:
                args = [*args, "--no-input"]
            execute_from_command_line(["__main__.py", command, *args])
            output = buf.getvalue()
        except Exception as e:
            output = str(e)
    return output


def manage(event, context=None):
    output_buffer = run_command(event["body"]["command"],
                                event["body"].get("args") or [])
    return {
            'statusCode': 200,
            'body': output_buffer,
            }
