{% load applescript_tags %}

on ends_with(theText, theSuffix)
    set suffixLength to length of theSuffix
    if length of theText is less than suffixLength then return false
        if text -suffixLength thru -1 of theText is equal to theSuffix then
            return true
        else
            return false
    end if
end ends_with

tell application "Microsoft Excel"
    tell workbook "{{ workbook_name }}"
        tell sheet "{{ sheet_name }}"
            -- 1. 원본 데이터 범위와 대상 셀 지정
            set sourceRange to range "{{ source_range_address }}" of it
            set destRange to range "{{ dest_range_address }}" of it

            -- 피벗 테이블 생성 (range1: 피벗 테이블 시작 위치)
            set pvtTable to make new pivot table at it with properties ¬
            { ¬
                source data:sourceRange ¬
                , table range1:destRange ¬
                {% if pivot_table_name %}, name:"{{ pivot_table_name }}"{% endif %} ¬
            }

            -- 행·열 필드 추가
            add fields to pivot table pvtTable ¬
            {% if row_field_names_list %}row fields {{ row_field_names_list|applescript_list }}{% endif %} ¬
            {% if column_field_names_list %}column fields {{ column_field_names_list|applescript_list }}{% endif %} ¬
            {% if page_field_names_list %}page fields {{ page_field_names_list|applescript_list }}{% endif %} ¬
            with add to table

            {% if value_fields %}
                {% for field in value_fields %}
                    set pivot field orientation of pivot field "{{ field.field_name }}" of pvtTable to orient as data field
                {% endfor %}

                set pfList to data fields of pvtTable
                repeat with i from 1 to count of pfList
                    set pf to item i of pfList
                    set fieldName to name of pf
                    {% for field in value_fields %}
                    if my ends_with(fieldName, "{{ field.field_name }}") then
                        set function of pf to {{ field.agg_func.value }}
                    end if
                    {% endfor %}
                end repeat
            {% endif %}

            -- TODO: style 적용
            set table style2 of pvtTable to "PivotStyleMedium2"

            set pvt_name to name of pvtTable
			do shell script "echo " & quoted form of pvt_name

        end tell
    end tell
end tell
