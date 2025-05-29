-- Get emails from Outlook folder
-- Parameters from template: max_hours, query, folder_type, folder_name

{% include 'helpers.applescript' %}

tell application "Microsoft Outlook"
    try
        -- Select target folder
        {% if folder_name %}
        set targetFolder to mail folder "{{ folder_name }}"
        {% elif folder_type == 'SENT' %}
        set targetFolder to sent mail
        {% elif folder_type == 'DRAFTS' %}
        set targetFolder to drafts
        {% elif folder_type == 'DELETED' %}
        set targetFolder to deleted items
        {% else %}
        set targetFolder to inbox
        {% endif %}
        
        -- Calculate cutoff date
        set cutoffDate to (current date) - ({{ max_hours }} * hours)
        
        -- Get messages from folder
        set messageList to messages of targetFolder whose time received > cutoffDate
        
        -- Apply search filter if provided
        {% if query %}
        set filteredList to {}
        repeat with aMessage in messageList
            if subject of aMessage contains "{{ query }}" then
                set end of filteredList to aMessage
            end if
        end repeat
        set messageList to filteredList
        {% endif %}
        
        -- Build CSV output
        set csvData to ""
        set csvData to csvData & "identifier,subject,sender_name,sender_email,to,cc,received_at" & linefeed
        
        repeat with aMessage in messageList
            try
                -- Get message ID
                set msgId to id of aMessage as string
                
                -- Get basic properties
                set msgSubject to my escape_csv(subject of aMessage)
                set msgSenderName to my escape_csv(name of sender of aMessage)
                
                -- Get sender email
                try
                    set msgSenderEmail to email address of address of sender of aMessage
                on error
                    set msgSenderEmail to ""
                end try
                
                -- Get recipients
                set toRecipients to {}
                repeat with r in to recipients of aMessage
                    set end of toRecipients to email address of address of r
                end repeat
                set msgTo to my escape_csv(my join_list(toRecipients, "; "))
                
                -- Get CC recipients
                set ccRecipients to {}
                repeat with r in cc recipients of aMessage
                    set end of ccRecipients to email address of address of r
                end repeat
                set msgCC to my escape_csv(my join_list(ccRecipients, "; "))
                
                -- Get received date
                set msgDate to my format_date(time received of aMessage)
                
                -- Build CSV line
                set csvLine to msgId & "," & msgSubject & "," & msgSenderName & "," & msgSenderEmail & "," & msgTo & "," & msgCC & "," & msgDate
                set csvData to csvData & csvLine & linefeed
                
            on error errMsg
                -- Skip problematic messages
            end try
        end repeat
        
        return csvData
        
    on error errMsg
        return "ERROR: " & errMsg
    end try
end tell