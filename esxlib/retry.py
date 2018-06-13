import time


def retry(func, *args, **kwargs):
    val = None
    for i in range(1, 4):
        try:
            val = func(*args, **kwargs)
        except Exception as e:
            print e
            #print "Retrying", func.__name__
            time.sleep(10)
            continue
        else:
            break
    return val
