import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

def index(request):
    return web.Response(body='<h1>Awesome</h1>'.encode('utf-8'),content_type='text/html')



async def init(loop):
    #创建web服务器实例
    app = web.Application(loop=loop)
    #将url注册进route
    app.router.add_route('GET', '/', index)
    #loop创建一个监听服务
    srv = await loop.create_server(app._make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()