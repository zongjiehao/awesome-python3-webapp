import aiomysql,logging
import asyncio
#创建连接池
# async def create_pool(loop,**kw):
#     logging.info("create database connection pool ...")
#     global __pool
#     __pool = await create_pool(
#         host = kw.get('host','localhost'),
#         port = kw.get('port','3306'),
#         user = kw['user'],
#         password = kw['password'],
#         db = kw['db'],
#         charset = kw.get('charset','utf-8'),
#         autocommit = kw.get('autocommit',True),
#         maxsize = kw.get('maxsize','10'),
#         minsize = kw.get('minsize','1'),
#         loop = loop
#     )

@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )
async def destory_pool():
    global __pool
    if __pool is not None :
        __pool.close()
        await __pool.wait_closed()

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
__new__()方法接收到的参数依次是：
cls为当前准备创建的类的对象 
name为类的名字，创建User类，则name便是User
bases类继承的父类集合,创建User类，则base便是Model
attrs为类的属性/方法集合，创建User类，则attrs便是一个包含User类属性的dict
'''
class ModelMetaclass(type):
    def __new__(cls,name,bases,attrs):
        #排除Model类本身
        if name == 'Model':
            return type.__new__(cls,name,bases,attrs)
        #获取table名称
        tableName = attrs.get('__table__',None) or name
        logging.info('found model:%s (table:%s)' %(name,tableName))
        #存储所有的字段
        mappings = dict()
        #仅用来存储非主键以外的其它字段，而且只存key
        fields=[]
        #保存主键的key
        primaryKey = None
        # 注意这里attrs的key是字段名，value是字段实例，不是字段的具体值
        # 比如User类的id=StringField(...) 这个value就是这个StringField的一个实例，而不是实例化
        # 的时候传进去的具体id值
        for k,v in attrs.items():
            if isinstance(v,Field):
                mappings[k] = v
                if v.primary_key:
                    #找到主键
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('PrimaryKey not found')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        attrs['__select__'] = "select %s, %s from %s" % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = "insert into %s (%s, %s) values (%s)" % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = "update %s set %s where %s=?" % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = "delete from %s where %s=? " % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

class Model(dict,metaclass=ModelMetaclass):
    def __init__(self,**kw):
        super().__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value = getattr(self,key,None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                setattr(self,key,value)
                logging.debug('using default value for %s: %s' % (key, str(value)))
        return value
    #根据where条件查找
    @classmethod
    async def findAll(cls,where=None,args=None,**kw):
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args=[]
        orderBy = kw.get('orderBy',None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit',None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit,int):
                sql.append(limit)
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit) == 2:
                sql.append('?,?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql),args,1)
        # **r 是关键字参数，构成了一个cls类的列表，其实就是每一条记录对应的类实例
        return [cls(**r) for r in rs]

    @classmethod
    #findNumber() - 根据WHERE条件查找，但返回的是整数，适用于select count(*)类型的SQL。
    async def findNumber(cls,selectField,where=None,args=None):
        sql = ['select %s _num_ from `%s`' %(selectField,cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql),args,1)
        if len(rs)==0:
            return None
        return rs[0]['num']

    @classmethod
    async def find(cls,pk):
        rs = await select('%s where `%s`=?' %(cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs)==0:
            return None
        return cls(**rs[0])

    async def save(self):
        args=list(map(self.getValueOrDefault,self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows=await execute(self.__insert__,args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue,self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__,args)
        if rows != 1:
            logging.warning('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__,args)
        if rows != 1:
            logging.warning('failed to remove by primary key: affected rows: %s' % rows)


