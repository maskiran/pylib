import time


def update(obj):
    return
    mor = None
    if hasattr(obj, 'mor'):
        mor = obj.mor
    elif hasattr(obj, 'update'):
        mor = obj
    if not mor:
        raise Exception('Cannot updated the obj. Its not mor', obj)

    for i in range(1,4):
        try:
            mor.update()
        except:
            if hasattr(mor, 'name'):
                print "Could not update mor %s" % mor.name
            else:
                print "Could not update mor %s" % mor
            if i != 3:
                print "Retrying.."
                time.sleep(i*10)
            continue
        else:
            # no error, update successful
            break

