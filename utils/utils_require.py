import os
from functools import wraps

from utils.utils_request import request_failed

MAX_CHAR_LENGTH = 255
MAX_TEXT_LENGTH = 3000

# A decorator function for checking if the current working directory is /opt/tmp
def CheckPath(check_fn):
    @wraps(check_fn)
    def decorated(*args, **kwargs):
        if os.getcwd() != "/opt/tmp":
            return request_failed("Invalid path. Please change to /opt/tmp.", 400)
        return check_fn(*args, **kwargs)
    return decorated


# A decorator function for processing `require` in view function.
def CheckRequire(check_fn):
    @wraps(check_fn)
    def decorated(*args, **kwargs):
        try:
            return check_fn(*args, **kwargs)
        except Exception as e:
            # Handle exception e
            return request_failed(e.args[0], 400)  # Refer to below
    return decorated


def require(body, key, type="string", err_msg=None, strict=True):

    if not strict:
        if key not in body.keys():
            return None
    
    if key not in body.keys():
        raise KeyError(err_msg if err_msg is not None 
                       else f"Invalid parameters. Expected `{key}`, but not found.")
    
    val = body[key]
    
    err_msg = f"Invalid parameters. Expected `{key}` to be `{type}` type."\
                if err_msg is None else err_msg
    
    if type == "int":
        try:
            val = int(val)
            return val
        except:
            raise KeyError(err_msg)
    
    elif type == "float":
        try:
            val = float(val)
            return val
        except:
            raise KeyError(err_msg)
    
    elif type == "string":
        try:
            val = str(val)
            return val
        except:
            raise KeyError(err_msg)
    
    elif type == "list":
        try:
            assert isinstance(val, list)
            return val
        except:
            raise KeyError(err_msg)

    else:
        raise NotImplementedError(f"Type `{type}` not implemented.")