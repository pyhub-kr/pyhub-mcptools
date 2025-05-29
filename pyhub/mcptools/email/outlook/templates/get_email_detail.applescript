-- Get detailed information about a specific email
-- Parameters from template: email_id

{% include 'helpers.applescript' %}

tell application "Microsoft Outlook"
    try
        -- Find message by ID
        set theMessage to message id {{ email_id }}
        
        -- Build structured output
        set output to ""
        set output to output & "=== EMAIL DETAILS ===" & linefeed
        
        -- Basic properties
        set output to output & "identifier: " & (id of theMessage as string) & linefeed
        set output to output & "subject: " & subject of theMessage & linefeed
        set output to output & "sender_name: " & name of sender of theMessage & linefeed
        
        -- Sender email
        try
            set output to output & "sender_email: " & email address of address of sender of theMessage & linefeed
        on error
            set output to output & "sender_email: " & linefeed
        end try
        
        -- Recipients
        set toRecipients to {}
        repeat with r in to recipients of theMessage
            set end of toRecipients to email address of address of r
        end repeat
        set output to output & "to: " & my join_list(toRecipients, "; ") & linefeed
        
        -- CC recipients
        set ccRecipients to {}
        repeat with r in cc recipients of theMessage
            set end of ccRecipients to email address of address of r
        end repeat
        set output to output & "cc: " & my join_list(ccRecipients, "; ") & linefeed
        
        -- Date
        set output to output & "received_at: " & my format_date(time received of theMessage) & linefeed
        
        -- Body
        set output to output & "=== BODY START ===" & linefeed
        set output to output & content of theMessage & linefeed
        set output to output & "=== BODY END ===" & linefeed
        
        -- Attachments
        set attachmentCount to count of attachments of theMessage
        set output to output & "attachment_count: " & attachmentCount & linefeed
        
        if attachmentCount > 0 then
            set output to output & "=== ATTACHMENTS ===" & linefeed
            repeat with att in attachments of theMessage
                set output to output & "filename: " & name of att & linefeed
                set output to output & "size: " & (file size of att) & linefeed
            end repeat
        end if
        
        -- Try to get HTML content if available
        try
            set htmlContent to source of theMessage
            if htmlContent contains "<html" or htmlContent contains "<HTML" then
                set output to output & "=== HTML AVAILABLE ===" & linefeed
            end if
        on error
            -- No HTML content
        end try
        
        return output
        
    on error errMsg
        return "ERROR: " & errMsg
    end try
end tell