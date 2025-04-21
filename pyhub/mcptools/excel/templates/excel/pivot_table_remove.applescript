{% load applescript_tags %}

tell application "Microsoft Excel"
    tell workbook "{{ workbook_name }}"
        tell sheet "{{ sheet_name }}"

            set buffer to ""

            {% if remove_all %}
                set remove_all to true
                set names_to_remove to {}
            {% else %}
                set remove_all to false
                set names_to_remove to {{ names|applescript_list }}
            {% endif %}

			set pivotCount to count pivot tables of it

			if (pivotCount) > 0 then
				set pivotList to pivot tables of it
				-- 역순으로 반복: 삭제 시 인덱스 꼬임 방지
				repeat with i from pivotCount to 1 by -1
					set pvt to item i of pivotList
					set pvt_name to name of pvt

					if remove_all is true or pvt_name is in names_to_remove then
						try
							set rng to table range2 of pvt
							clear formats of rng
							clear contents of rng

							set buffer to buffer & "[DELETED] " & pvt_name & linefeed
						on error errMsg
							set buffer to buffer & "[FAILED] " & pvt_name & " - " & errMsg & linefeed
						end try
					end if
				end repeat
			else
				set buffer to buffer & "No pivot tables were removed."
			end if

            do shell script "echo " & quoted form of buffer
        end tell
    end tell
end tell
