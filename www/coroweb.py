import os,asyncio,inspect,logging,functools
from urllib import parse
from aiohttp import web
from www.apis import APIError
#定义装饰器@get('/path')
def get(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

#定义装饰器@post('/path')
def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator
'''
def foo(a, *b, c, **d, e=5):
    pass        

a == POSITIONAL_OR_KEYWORD # a是用位置或参数名都可赋值的，位置参数或者命名关键字参数
b == VAR_POSITIONAL        # b是可变长列表，可变参数
c == KEYWORD_ONLY          # c只能通过参数名的方式赋值，命名关键字参数
d == VAR_KEYWORD           # d是可变长字典,关键字参数
e == POSITIONAL_OR_KEYWORD # 位置参数或者命名关键字参数
'''
#收集没有默认值的命名关键字参数
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind ==inspect.Parameter.KEYWORD_ONLY and param.default==inspect.Parameter.empty:
            args.append(name)
    return tuple(args)
#收集命名关键字参数
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

#判断是否有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

#判断有没有关键字参数
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

#判断是否有名叫'request'的参数,且该参数是否为最后一个参数
def has_request_arg(fn):
    params = inspect.signature(fn).parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and param.kind == inspect.Parameter.POSITIONAL_ONLY:
            raise ValueError(
                'request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(inspect.signature(fn))))
    return found

'''
RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，
URL函数不一定是一个coroutine，因此我们用RequestHandler()来封装一个URL处理函数。
调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求：
'''
class RequestHandler(object):# 初始化一个请求处理类
    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):#一个类实现了__call__方法()，就可以把类当实例调用
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._has_request_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest(text='Missing Content-Type')
                ct = request.content_type.lower()
                #json格式的请求
                if ct.startwith('application/json'):
                    #返回body中的json串，如果body中不是json会抛出异常
                    params = await request.json()
                    if not isinstance(params.dict):
                        return web.HTTPBadRequest(text='Json body must be object')
                    kw = params
                #form表单请求的编码格式
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    # 返回post的内容中解析后的数据。dict-like对象
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                # 返回URL查询语句，?后的键值。string形式。
                qs = request.query_string
                if qs:
                    kw=dict()
                    #true表示不忽略空格
                    '''
                    解析url中?后面的键值对的内容 
                    qs = 'first=f,s&second=s' 
                    parse.parse_qs(qs, True).items() 
                    >>> dict([('first', ['f,s']), ('second', ['s'])]) 
                    '''
                    for k, v in parse.parse_qs(qs,True).items():
                        kw[k] == v[0]
        if kw is None:#如果request中没有参数
            # request.match_info返回dict对象。可变路由中的可变字段{variable}为参数名，传入request请求的path为值
            # 若存在可变路由：/a/{name}/c，可匹配path为：/a/jack/c的request
            # 则request.match_info返回{name = jack}
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                copy = dict()
            #只保留命名关键字参数
            for name in self._named_kw_args:
                if name in kw:
                    copy[name] = kw[name]
                kw = copy
            #检查kw中的参数是否和match_info中的相同
            for k, v in request.match_info.items():
                #检查kw中的参数是否和match_info中的相同
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        #视图函数中存在request参数
        if self._has_request_arg:
            kw['request'] = request
            # check required kw:
        #视图函数中存在没有默认值的命名关键字参数
        if self._required_kw_args:
            for name in self._required_kw_args:
                #如果没有传入必须的参数
                if not name in kw:
                    return web.HTTPBadRequest(text='Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)