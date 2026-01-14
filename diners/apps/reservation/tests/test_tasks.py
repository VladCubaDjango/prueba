from django.test import TestCase
import datetime
from django.utils import timezone
from diners.apps.reservation.tasks import create_transaction_task, remove_reservations_for_category_schedule
from diners.apps.reservation.models import MealSchedule, Menu, ReservationCategory, Reservation


def make_menu_with_reservation(date_offset_days=1):
    schedule = MealSchedule.objects.create(name='Lunch')
    menu_date = datetime.date.today() + datetime.timedelta(days=date_offset_days)
    menu = Menu.objects.create(schedule=schedule, date=menu_date)
    category = ReservationCategory.objects.create(name='TestCat')
    reservation = Reservation.objects.create(menu=menu, reservation_category=category, reserv_log_user='tester')
    return category, schedule, menu, reservation


class TasksTestCase(TestCase):
    def test_create_transaction_task_returns_mock_response(self):
        # run task synchronously
        result = create_transaction_task.apply(
            args=(
                'diners_reservation_test',
                10.0,
                'test',
                123,
                'CR',
                'unittest'
            )
        ).get()
        self.assertIsInstance(result, dict)
        self.assertIn('data', result)

    def test_remove_reservations_for_category_schedule_deletes_future_reservations(self):
        category, schedule, menu, reservation = make_menu_with_reservation(date_offset_days=2)
        # ensure reservation exists
        self.assertEqual(Reservation.objects.filter(pk=reservation.pk).count(), 1)

        # call the task
        res = remove_reservations_for_category_schedule.apply(args=(category.pk, schedule.pk)).get()
        self.assertTrue(res)
        # reservation should be deleted
        self.assertEqual(Reservation.objects.filter(pk=reservation.pk).count(), 0)

    def test_reservcatschedule_delete_triggers_task_and_deletes_reservations(self):
        category, schedule, menu, reservation = make_menu_with_reservation(date_offset_days=3)
        # create the ReservCatSchedule linking both
        rcs = ReservationCategory.meal_schedules.through.objects.create(mealschedule=schedule, reservation_category=category, count_diners=1)
        # ensure reservation exists
        self.assertEqual(Reservation.objects.filter(pk=reservation.pk).count(), 1)
        # delete the ReservCatSchedule - signal should enqueue task and in eager mode run synchronously
        rcs.delete()
        # reservation should be deleted
        self.assertEqual(Reservation.objects.filter(pk=reservation.pk).count(), 0)

    def test_create_transaction_task_delay_executes_in_eager_mode(self):
        # ensure Celery runs tasks eagerly in this test
        from diners.celery import app as celery_app
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        result = create_transaction_task.delay('diners_reservation_test', 5.0, 'test', 456, 'CR', 'unittest')
        # in eager mode .get() should return the result of the task
        data = result.get()
        self.assertIsInstance(data, dict)

    def test_remove_reservations_task_delay_executes_and_deletes(self):
        from diners.celery import app as celery_app
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        category, schedule, menu, reservation = make_menu_with_reservation(date_offset_days=2)
        # call via .delay() which should execute eagerly in this test
        res = remove_reservations_for_category_schedule.delay(category.pk, schedule.pk)
        self.assertTrue(res.get())
        self.assertEqual(Reservation.objects.filter(pk=reservation.pk).count(), 0)
