import os,asyncio,inspect,logging,functools
from urllib import parse
from aiohttp import web

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

