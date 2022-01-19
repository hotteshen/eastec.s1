import asyncio
import json
from multiprocessing import Process
import socket
try:
    from asyncio.exceptions import TimeoutError
except:
    # for Python 3.7 of Raspberry OS
    from concurrent.futures._base import TimeoutError

import httpx
import typer
import uvicorn
import websockets

from .conf import TEMP_DELTA
from .kfive import KFive
from .sone import SOne
from .utils import Logger, get_sauna_id


LOCAL_HOST = '0.0.0.0'
LOCAL_PORT = 8000
CLOUD_HOST = '0.0.0.0'
CLOUD_PORT = 8001

typer_app = typer.Typer()
logger = Logger.instance()


async def loop_ws_client(cloud_url: str, local_url: str):
    sauna_id = get_sauna_id()
    if cloud_url.endswith('/'):
        cloud_url = cloud_url[:-1]
    if not (cloud_url.startswith("http://") or cloud_url.startswith("https://")):
        logger.error("Invalid cloud URL form.")
        return
    ws_cloud_url = f"ws://{cloud_url.split('://')[1]}/ws/{sauna_id}"
    logger.log(f"Connecting to {ws_cloud_url}")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                async with websockets.connect(ws_cloud_url) as ws:
                    logger.log("websocket connected")
                    while True:
                        req = await ws.recv()
                        req = json.loads(req)
                        logger.log(f"from cloud server: {req}")
                        req = client.build_request(
                            req['method'],
                            f"{local_url}{req['path']}",
                            json=req['body'])
                        res = await client.send(req)
                        await ws.send(json.dumps({"status_code": res.status_code, "body": res.json()}))
            except websockets.exceptions.InvalidStatusCode:
                logger.error("Invalid server response for websocket, check Cloud URL and networking. Retrying in 5 seconds.")
            except socket.gaierror:
                logger.warn("Name or service not known, check Cloud URL and networking. Retrying in 5 seconds.")
            except ConnectionRefusedError:
                logger.warn("Connect call failed, check Cloud URL and networking. Retrying in 5 seconds.")
            except TimeoutError:
                logger.error("Timeout error, check Cloud URL and networking. Retrying in 5 seconds.")
            except websockets.exceptions.ConnectionClosedError:
                logger.error("Connection closed, check Cloud URL and networking. Retrying in 5 seconds.")
            except OSError:
                logger.warn("Connect call failed, check if the port is open on server side.")
            await asyncio.sleep(5)

async def stateupdater(sone: SOne):
    while True:
        await asyncio.sleep(1)
        await sone.check_heating()


@typer_app.command()
def device(cloud_url=None, host: str=LOCAL_HOST, port: int=LOCAL_PORT):
    'run local API server'
    from . import api_local

    if cloud_url is None:
        cloud_url = f"http://{CLOUD_HOST}:{CLOUD_PORT}"

    def run_app():
        KFive.instance().init_uart()
        from .io import init_gpio
        init_gpio()
        uvicorn.run(api_local.app, host=host, port=port)

    def run_ws():
        try:
            asyncio.run(loop_ws_client(cloud_url, local_url=f"http://{host}:{port}"))
        except KeyboardInterrupt:
            logger.log("Stopping by the user.")

    def run_stateupdater():
        try:
            asyncio.run(stateupdater(api_local.sone))
        except KeyboardInterrupt:
            logger.log("Stopping by the user.")

    app_proc = Process(target = run_app)
    ws_proc = Process(target = run_ws)
    stateupdater_proc = Process(target = run_stateupdater)
    app_proc.start()
    ws_proc.start()
    stateupdater_proc.start()
    app_proc.join()
    ws_proc.join()
    stateupdater_proc.join()


@typer_app.command()
def cloud(host: str=CLOUD_HOST, port: int=CLOUD_PORT):
    'run cloud API server'
    from . import api
    uvicorn.run(api.app, host=host, port=port)


typer_app()
