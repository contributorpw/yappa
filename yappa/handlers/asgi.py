import json
import logging
from pathlib import Path

import httpx

from yappa.handlers.wsgi import load_app, patch_response
from yappa.settings import DEFAULT_CONFIG_FILENAME
from yappa.utils import load_yaml

logger = logging.getLogger(__name__)


async def call_app(app, event):
    async with httpx.AsyncClient(app=app,
                                 base_url=event["headers"].get("Host",
                                                               "https://raw_function.net")) as client:
        request = client.build_request(
                method=event["httpMethod"],
                url=event["url"],
                headers=event["headers"],
                params=event["queryStringParameters"],
                content=json.dumps(event["body"]).encode(),
                )
        response = await client.send(request)
        return response


try:
    config = load_yaml(Path(Path(__file__).resolve().parent.parent,
                            DEFAULT_CONFIG_FILENAME))

    app = load_app(config.get("entrypoint"),
                   config.get("DJANGO_SETTINGS_MODULE"))
except ValueError:
    logger.warning("Looks like broken Yappa config is used")


async def handle(event, context):
    response = await call_app(app, event)
    if not config["debug"]:
        return patch_response(response)
    return {
            'statusCode': 200,
            'body': {
                    "event": event,
                    "response": response,
                    },
            }
