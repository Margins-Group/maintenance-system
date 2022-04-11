from django.test import TestCase

from printer_support.models import *


class TestClientModel(TestCase):
    def test_model_str(self):
        client_name = Client.objects.create(client_name='TEST')
        address = Client.objects.create(address='Accra')
        self.assert_(str(client_name), 'TEST')


class TestPartModel(TestCase):
    def test_model_str(self):
        name = Part.objects.create(name='TEST')
        self.assert_(str(name), 'TEST')


class TestProfileModel(TestCase):
    def test_model_str(self):
        user_test = User.objects.create(email='testing@gmail.com', first_name='TestA', last_name='TestB', password='Testing')

        Profile.user._set_pk_val = user_test.pk
        self.assert_(bool(user_test), 'TestA TestB')


class TestPrinterModel(TestCase):
    def test_model_str(self):
        client_test = Client.objects.create(client_name='TEST')

        printer_number = Printer.objects.create(printer_number='C00000', client_id=client_test.pk)
        self.assert_(str(printer_number), 'C00000')


class TestScheduleModel(TestCase):
    def test_model_str(self):
        user_test = User.objects.create(email='testing@gmail.com', first_name='TestA', last_name='TestB',
                                        password='Testing')

        client_test = Client.objects.create(client_name='TEST')

        printer_number = Schedule.objects.create(printer_number='C00000', pickup_date='2021-3-15', user_id=user_test.pk,
                                                 client_id=client_test.pk)
        self.assert_(str(printer_number), 'C00000')


class TestEventModel(TestCase):
    def test_model_str(self):
        user_test = User.objects.create(email='testing@gmail.com', first_name='TestA', last_name='TestB',
                                        password='Testing')

        action = Event.objects.create(action='Writing test code', user_id=user_test.pk)
        self.assert_(str(user_test), 'TestA TestB')


class TestPartEventModel(TestCase):
    def test_model_str(self):
        user_test = User.objects.create(email='testing@gmail.com', first_name='TestA', last_name='TestB',
                                        password='Testing')

        action = PartEvent.objects.create(action='Writing test code', user_id=user_test.pk)
        self.assert_(str(user_test), 'TestA TestB')


class UserModel(TestCase):
    def test_model_str(self):
        user_test = User.objects.create(email='testing@gmail.com', first_name='TestA', last_name='TestB',
                                        password='Testing')

        self.assert_(str(user_test), 'TestA TestB')
