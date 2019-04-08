from www import config_default
class Dict(dict):
    # 支持使用类的属性查询信息的方法
    def __init__(self,name=(),values=(),**kw):
        super(Dict.self).__init__(**kw)
        for k,v in zip(name,values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except:
            return AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def merge(defaults,override):
        r = {}
        for k, v in defaults.items():
            pass

