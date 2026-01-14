import importlib, time
try:
    importlib.import_module('diners.apps.reservation.tasks')
    print('tasks imported')
except Exception as e:
    print('import error:', type(e).__name__, e)

# wait briefly
time.sleep(0.2)
