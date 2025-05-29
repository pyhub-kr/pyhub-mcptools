-- Send email via Outlook
-- Parameters from template: subject, message, from_email, recipients, cc_list, bcc_list, attachments

{% include 'helpers.applescript' %}

tell application "Microsoft Outlook"
    try
        -- Create new outgoing message
        set theMessage to make new outgoing message with properties {subject:"{{ subject }}", content:"{{ message }}"}
        
        -- Set sending account if specified
        {% if from_email %}
        try
            set accountFound to false
            repeat with acc in exchange accounts
                if email address of acc is "{{ from_email }}" then
                    set account of theMessage to acc
                    set accountFound to true
                    exit repeat
                end if
            end repeat
            
            if not accountFound then
                repeat with acc in pop accounts
                    if email address of acc is "{{ from_email }}" then
                        set account of theMessage to acc
                        set accountFound to true
                        exit repeat
                    end if
                end repeat
            end if
            
            if not accountFound then
                repeat with acc in imap accounts
                    if email address of acc is "{{ from_email }}" then
                        set account of theMessage to acc
                        set accountFound to true
                        exit repeat
                    end if
                end repeat
            end if
        on error
            -- Continue with default account
        end try
        {% endif %}
        
        -- Add TO recipients
        {% for recipient in recipients %}
        make new recipient at theMessage with properties {email address:{address:"{{ recipient }}"}}
        {% endfor %}
        
        -- Add CC recipients
        {% if cc_list %}
        {% for cc in cc_list %}
        make new cc recipient at theMessage with properties {email address:{address:"{{ cc }}"}}
        {% endfor %}
        {% endif %}
        
        -- Add BCC recipients
        {% if bcc_list %}
        {% for bcc in bcc_list %}
        make new bcc recipient at theMessage with properties {email address:{address:"{{ bcc }}"}}
        {% endfor %}
        {% endif %}
        
        -- Add attachments
        {% if attachments %}
        {% for attachment in attachments %}
        make new attachment at theMessage with properties {file:"{{ attachment }}" as POSIX file}
        {% endfor %}
        {% endif %}
        
        -- Send or display the message
        {% if compose_only %}
        -- Just display the compose window
        activate
        open theMessage
        return "SUCCESS: Email compose window opened"
        {% else %}
        -- Send the message
        send theMessage
        return "SUCCESS: Email sent successfully"
        {% endif %}
        
    on error errMsg
        return "ERROR: " & errMsg
    end try
end tell