import django
from django.conf import settings
from diners.apps.reservation.tasks import create_transaction_task, remove_reservations_for_category_schedule

# Ensure we are using local settings
print('DJANGO SETTINGS:', settings.SETTINGS_MODULE)
# Make sure Django app registry is ready for model imports inside tasks
django.setup()

print('Calling create_transaction_task.apply...')
res = create_transaction_task.apply(kwargs={
    'action': 'test_action',
    'amount': 12.5,
    'description': 'Test transaction',
    'person': 1,
    'type_': 'CR',
    'user': 'test_user'
})
print('create_transaction_task result (apply):', res.get())

print('Calling remove_reservations_for_category_schedule.apply...')
res2 = remove_reservations_for_category_schedule.apply(args=(1, 1))
print('remove_reservations_for_category_schedule result (apply):', res2.get())
