from django.test import TestCase, SimpleTestCase

from printer_support.forms import *


class TestAddPrinterForm(TestCase):
    def test_printer_number_format(self):
        form_data = {'printer_number': 'c00000'}
        form = AddPrinterForm(data=form_data)
        self.assert_(bool(form_data), 'C00000')

    def test_box_number_format(self):
        form_data = {'box_number': 'c00000'}
        form = AddPrinterForm(data=form_data)
        self.assert_(bool(form_data), 'C00000')


class TestUpdatePrinterForm(TestCase):
    def test_printer_number_format(self):
        form_data = {'printer_number': 'c00000'}
        form = UpdatePrinterForm(data=form_data)
        self.assert_(bool(form_data), 'C00000')

    def test_box_number_format(self):
        form_data = {'box_number': 'c00000'}
        form = UpdatePrinterForm(data=form_data)
        self.assert_(bool(form_data), 'C00000')


class TestUpdateScheduleForm(TestCase):
    def test_printer_number_format(self):
        form_data = {'printer_number': 'c00000'}
        form = UpdateScheduleForm(data=form_data)
        self.assert_(bool(form_data), 'C00000')


class TestBothUpdateScheduleForm(TestCase):
    def test_old_head_barcode_format(self):
        form_data = {'old_head_barcode': '22222'}
        form = BothUpdateScheduleForm(data=form_data)
        self.assert_(bool(form_data), 'CQUH22222')

    def test_new_head_barcode_format(self):
        form_data = {'new_head_barcode': '33333'}
        form = BothUpdateScheduleForm(data=form_data)
        self.assert_(bool(form_data), 'CQUH33333')


class TestFixedUpdateScheduleForm(TestCase):
    def test_old_head_barcode_format(self):
        form_data = {'old_head_barcode': '22222'}
        form = FixedUpdateScheduleForm(data=form_data)
        self.assert_(bool(form_data), 'CQUH22222')

    def test_new_head_barcode_format(self):
        form_data = {'new_head_barcode': '33333'}
        form = FixedUpdateScheduleForm(data=form_data)
        self.assert_(bool(form_data), 'CQUH33333')


class TestAddPartForm(TestCase):
    def test_part_name_format(self):
        form_data = {'part_name': 'head'}
        form = AddPartForm(data=form_data)
        self.assert_(bool(form_data), 'HEAD')

    def test_number_of_parts_available_format(self):
        form_data = {'number_of_parts_available': -8}
        form = AddPartForm(data=form_data)
        self.assert_(bool(form_data), 8)


class TestUpdatePartForm(TestCase):
    def test_part_name_format(self):
        form_data = {'name': 'head'}
        form = UpdatePartForm(data=form_data)
        self.assert_(bool(form_data), 'HEAD')

    def test_available_number_format(self):
        form_data = {'available_number': -8}
        form = UpdatePartForm(data=form_data)
        self.assert_(bool(form_data), 8)


class TestUpdateStockForm(TestCase):
    def test_available_number_format(self):
        form_data = {'number_of_parts_available': -8}
        form = UpdateStockForm(data=form_data)
        self.assert_(bool(form_data), 8)


class TestRequestPartForm(TestCase):
    def test_available_number_format(self):
        form_data = {'number_of_parts_available': 20}
        form = RequestPartForm(data=form_data)
        self.assert_(bool(form_data), 20)