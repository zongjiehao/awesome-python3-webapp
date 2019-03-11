import aiomysql,logging
import asyncio
#创建连接池
async def create_pool(loop,**kw):
    logging.info("create database connection pool ...")
    global __pool
    __pool = await create_pool(
        host = kw.get('host','localhost'),
        port = kw.get('port','3306'),
        user = kw['user'],
        password = kw['password'],
        db = kw['db'],
        charset = kw.get('charset','utf-8'),
        autocommit = kw.get('autocommit',True),
        maxsize = kw.get('maxsize','10'),
        minsize = kw.get('minsiez','1'),
        loop = loop
    )
def log(sql, args=()):
    logging.info('SQL: %s' % sql)

#执行select语句
async def select(sql, args, size=None):
    log(sql, args)
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs

async def execute(sql, args, autocommit=True):
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected

#创建sql占位符
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

#保存数据库的字段名和字段类型
class Field(object):
    def __init__(self,name,column_type,primary_key,default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s,%s:%s>' %(self.__class__.__name__,self.column_type,self.name)

#保存字符类型的字段
class StringField(Field):
    def __init__(self,name=None,primary_key=False,default=None,ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

#保存布尔类型的字段
class BooleanField(Field):
    def __init__(self,name=None,default=False):
        super().__init__(name,'boolean',False,default)
#保存整形类型字段
class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)
#保存浮点类型字段
class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)
#保存文本类型字段
class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

#建立模型元类
'''__new__() 是在新式类中新出现的方法,它作用在构造方法建造实例之前,
可以这么理解,在 Python 中存在于类里面的构造方法 __init__() 负责将类的实例化,
而在 __init__() 启动之前,__new__() 决定是否要使用该 __init__() 方法,
因为__new__() 可以调用其他类的构造方法或者直接返回别的对象来作为本类的实例.
'''
#class ModelMetaclass(type):




