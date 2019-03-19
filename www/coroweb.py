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
        wrapper.__route__ = 'path'
        return wrapper
    return decorator

#定义装饰器@post('/path')
def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = 'path'
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

#判断是否有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

#判断有没有关键字参数
def has_var_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

#判断是否有名叫'request'的参数,且该参数是否为最后一个参数
# def has_request_kw_args(fn):
#     params = inspect.signature(fn).parameters
#     found = False
#     for name, param in params.items():
#         if name == 'request':
#             found = True
#             continue
#         if found


