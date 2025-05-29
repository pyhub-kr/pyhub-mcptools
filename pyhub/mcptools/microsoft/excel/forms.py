import xlwings as xw
from django import forms

from pyhub.mcptools.core.fields import CommaSeperatedField
from pyhub.mcptools.microsoft.excel.types import ExcelAggregationType
from pyhub.mcptools.microsoft.excel.utils.tables import PivotTable


class PivotTableCreateForm(forms.Form):
    row_field_names = CommaSeperatedField(required=True)
    column_field_names = CommaSeperatedField(required=False)
    page_field_names = CommaSeperatedField(required=False)
    value_fields = CommaSeperatedField(separator="|", required=True)
    pivot_table_name = forms.CharField(required=False)

    def __init__(self, *args, source_range: xw.Range, dest_range: xw.Range, **kwargs):
        super().__init__(*args, **kwargs)

        self.source_range = source_range
        self.dest_range = dest_range

        # 소스 데이터의 컬럼명 집합 추출
        self.column_names_set = set(self.source_range[0].expand("right").value)

    def clean_value_fields(self) -> list[dict]:
        value_fields_list: list[str] = self.cleaned_data.get("value_fields")

        data_item_list = []
        # 값 필드 설정 (문자열 파싱)
        if value_fields_list:
            for item in value_fields_list:
                parts = item.split(":")

                field_name = parts[0]
                if field_name not in self.column_names_set:
                    raise forms.ValidationError(f"value_fields contain invalid field name: {field_name}")

                agg_func_name = parts[1] if len(parts) > 1 else "SUM"
                try:
                    agg_func = getattr(ExcelAggregationType, agg_func_name.upper())
                except AttributeError as e:
                    raise forms.ValidationError(f"Invalid aggregation function: {agg_func_name}") from e

                data_item_list.append(
                    {
                        "field_name": field_name,
                        "agg_func": agg_func,
                    }
                )

        return data_item_list

    def is_valid(self, raise_exception=False):
        ret = super().is_valid()
        if not ret and raise_exception:
            raise forms.ValidationError(self.errors)
        return ret

    def clean(self):
        cleaned_data = super().clean()

        row_field_names_list = self.cleaned_data.get("row_field_names", [])
        column_field_names_list = self.cleaned_data.get("column_field_names", [])
        page_field_names_list = self.cleaned_data.get("page_field_names", [])

        # 필드명 유효성 검사
        for field_list, field_type in [
            (row_field_names_list, "Row fields"),
            (column_field_names_list, "Column fields"),
            (page_field_names_list, "Page fields"),
        ]:
            invalid_fields = set(field_list) - self.column_names_set
            if invalid_fields:
                raise forms.ValidationError(f"{field_type} contain invalid field names: {', '.join(invalid_fields)}")

        return cleaned_data

    def save(self) -> str:
        pivot_table_name = self.cleaned_data["pivot_table_name"]

        created_pivot_table_name = PivotTable.create(
            source_range=self.source_range,
            dest_range=self.dest_range,
            row_field_names_list=self.cleaned_data["row_field_names"],
            column_field_names_list=self.cleaned_data["column_field_names"],
            page_field_names_list=self.cleaned_data["page_field_names"],
            value_fields=self.cleaned_data["value_fields"],
            pivot_table_name=pivot_table_name,
        )
        return created_pivot_table_name
