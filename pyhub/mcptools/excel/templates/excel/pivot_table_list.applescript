tell application "Microsoft Excel"
    tell workbook "{{ workbook_name }}"
        tell sheet "{{ sheet_name }}"
			set current_sheet_name to name of it
			set allPivots to pivot tables of it
			set buffer to ""

			repeat with pvtTable in allPivots
				set name_ to name of pvtTable
				set source_addr to source data of pvtTable

				try
					set dest_range to table range2 of pvtTable
					set dest_addr to get address of dest_range
					-- TODO: current_sheet_name이 올바르게 현재 대상을 가리키나?
					set dest_addr to current_sheet_name & "!" & dest_addr
				on error errMsg
					set dest_addr to "Error : " & errMsg
				end try

				set buffer to buffer & "name: " & "" & name_ & linefeed
				set buffer to buffer & "source_addr: " & source_addr & linefeed
				set buffer to buffer & "dest_addr: " & dest_addr & linefeed

				set row_field_names to {}
				set column_field_names to {}
				set page_field_names to {}
				set value_field_names to {}

				set fieldList to row fields of pvtTable -- column, page, value
				repeat with field in fieldList
					set field_name to name of field
					copy "\"" & field_name & "\"" to end of row_field_names
				end repeat

				set fieldList to column fields of pvtTable
				repeat with field in fieldList
					set field_name to name of field
					copy "\"" & field_name & "\"" to end of column_field_names
				end repeat

				set fieldList to page fields of pvtTable
				repeat with field in fieldList
					set field_name to name of field
					copy "\"" & field_name & "\"" to end of page_field_names
				end repeat

				set fieldList to data fields of pvtTable
				repeat with field in fieldList
					set field_name to name of field
					copy "\"" & field_name & "\"" to end of value_field_names
				end repeat

				set buffer to buffer & "row_field_names: [" & my join_list(row_field_names, ", ") & "]" & linefeed
				set buffer to buffer & "column_field_names: [" & my join_list(column_field_names, ", ") & "]" & linefeed
				set buffer to buffer & "page_field_names: [" & my join_list(page_field_names, ", ") & "]" & linefeed
				set buffer to buffer & "value_field_names: [" & my join_list(value_field_names, ", ") & "]" & linefeed

				-- 피벗 테이블 구분자
				if pvtTable is not last item of allPivots then
					set buffer to buffer & "---" & linefeed
				end if
			end repeat

			do shell script "echo " & quoted form of buffer
		end tell
	end tell
end tell

-- 유틸리티 함수들
on join_list(theList, delimiter)
	if theList is {} then
		return ""
	else
		set {oldDelimiters, AppleScript's text item delimiters} to {AppleScript's text item delimiters, delimiter}
		set joined to theList as string
		set AppleScript's text item delimiters to oldDelimiters
		return joined
	end if
end join_list
