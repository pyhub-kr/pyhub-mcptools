import unittest

from django import forms

from pyhub.mcptools.core.fields import CommaSeperatedField, IntegerCommaSeperatedField


class TestCommaSeperatedField(unittest.TestCase):
    def test_empty_value(self):
        field = CommaSeperatedField()
        self.assertEqual(field.to_python(""), [])
        self.assertEqual(field.to_python(None), [])

    def test_string_type(self):
        field = CommaSeperatedField()
        self.assertEqual(field.to_python("a,b,c"), ["a", "b", "c"])
        self.assertEqual(field.to_python(" a , b , c "), ["a", "b", "c"])


class TestIntegerCommaSeperatedField(unittest.TestCase):
    def test_empty_value(self):
        field = IntegerCommaSeperatedField()
        self.assertEqual(field.to_python(""), [])
        self.assertEqual(field.to_python(None), [])

    def test_int_type(self):
        field = IntegerCommaSeperatedField()
        self.assertEqual(field.to_python("1,2,3"), [1, 2, 3])
        self.assertEqual(field.to_python(" 1 , 2 , 3 "), [1, 2, 3])

    def test_validation_error(self):
        field = IntegerCommaSeperatedField()
        with self.assertRaises(forms.ValidationError):
            field.to_python("1,a,3")

    def test_in_form(self):
        class TestForm(forms.Form):
            string_list = CommaSeperatedField()
            int_list = IntegerCommaSeperatedField()

        form = TestForm(data={"string_list": "a,b,c", "int_list": "1,2,3"})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["string_list"], ["a", "b", "c"])
        self.assertEqual(form.cleaned_data["int_list"], [1, 2, 3])

    def test_required_field(self):
        class TestForm(forms.Form):
            required_field = IntegerCommaSeperatedField(required=True)
            optional_field = IntegerCommaSeperatedField(required=False)

        # 필수 필드가 없는 경우
        form = TestForm(data={"optional_field": "1,2,3"})
        self.assertFalse(form.is_valid())

        # 필수 필드가 있는 경우
        form = TestForm(data={"required_field": "1,2,3", "optional_field": ""})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["required_field"], [1, 2, 3])
        self.assertEqual(form.cleaned_data["optional_field"], [])
