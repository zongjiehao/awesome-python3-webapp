import orm
import asyncio,sys
from models import User, Blog, Comment


async def test(loop):
    await orm.create_pool(loop=loop, user='root', password='root', db='awesome')
    u = User(name='Test12', email='test12@example.com',passwd='1234567890', image='about:blank')
    await u.save()
    await orm.destory_pool()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
#loop.run_until_complete(asyncio.wait([test(loop)]))
loop.close()
# if loop.is_closed():
#     sys.exit(0)


