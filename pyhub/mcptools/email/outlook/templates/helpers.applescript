-- Helper functions for Outlook AppleScript templates

on escape_csv(str)
    -- Escape a string for CSV format
    if str contains "," or str contains "\"" or str contains linefeed or str contains return then
        set str to "\"" & my replace_text(str, "\"", "\"\"") & "\""
    end if
    return str
end escape_csv

on replace_text(this_text, search_string, replacement_string)
    -- Replace all occurrences of search_string with replacement_string
    set AppleScript's text item delimiters to the search_string
    set the item_list to every text item of this_text
    set AppleScript's text item delimiters to the replacement_string
    set this_text to the item_list as string
    set AppleScript's text item delimiters to ""
    return this_text
end replace_text

on format_date(date_obj)
    -- Format date object to ISO-like string
    try
        set y to year of date_obj
        set m to (month of date_obj as integer) as string
        if length of m = 1 then set m to "0" & m
        set d to day of date_obj as string
        if length of d = 1 then set d to "0" & d
        set h to hours of date_obj as string
        if length of h = 1 then set h to "0" & h
        set min to minutes of date_obj as string
        if length of min = 1 then set min to "0" & min
        set s to seconds of date_obj as string
        if length of s = 1 then set s to "0" & s
        
        return y & "-" & m & "-" & d & " " & h & ":" & min & ":" & s
    on error
        return ""
    end try
end format_date

on join_list(lst, delimiter)
    -- Join list items with delimiter
    set AppleScript's text item delimiters to delimiter
    set result to lst as string
    set AppleScript's text item delimiters to ""
    return result
end join_list