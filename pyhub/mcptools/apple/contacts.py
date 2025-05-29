"""Apple Contacts integration."""

from typing import Optional, List, Dict, Any

from pyhub.mcptools.apple.utils import (
    applescript_run,
    escape_applescript_string,
    parse_applescript_record,
)


class ContactsClient:
    """Client for interacting with Apple Contacts app."""

    async def search_contacts(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search contacts by name, email, or phone.

        Args:
            name: Name to search for (partial match)
            email: Email to search for
            phone: Phone number to search for
            limit: Maximum number of contacts to return

        Returns:
            List of contact dictionaries
        """
        # Build search conditions
        conditions = []
        if name:
            name_lower = name.lower()
            conditions.append(f'(nameLower contains "{escape_applescript_string(name_lower)}")')
        if email:
            conditions.append(f'(emailList contains "{escape_applescript_string(email)}")')
        if phone:
            # Remove non-digits for phone comparison
            phone_digits = ''.join(filter(str.isdigit, phone))
            conditions.append(f'(phoneList contains "{phone_digits}")')

        if not conditions:
            # If no search criteria, return recent contacts
            search_filter = "true"
        else:
            search_filter = " or ".join(conditions)

        script = f'''
        tell application "Contacts"
            set outputList to {{}}
            set contactCount to 0

            repeat with thePerson in people
                if contactCount ≥ {limit} then exit repeat

                -- Get contact details
                set fullName to ""
                try
                    set firstName to first name of thePerson as string
                    set lastName to last name of thePerson as string
                    if firstName is "missing value" then set firstName to ""
                    if lastName is "missing value" then set lastName to ""

                    if firstName is not "" and lastName is not "" then
                        set fullName to firstName & " " & lastName
                    else if firstName is not "" then
                        set fullName to firstName
                    else if lastName is not "" then
                        set fullName to lastName
                    else
                        set fullName to "Unknown"
                    end if
                on error
                    set fullName to "Unknown"
                end try

                set nameLower to do shell script "echo " & quoted form of fullName & " | tr '[:upper:]' '[:lower:]'"

                -- Get emails
                set emailList to {{}}
                try
                    repeat with theEmail in emails of thePerson
                        set end of emailList to value of theEmail as string
                    end repeat
                on error
                end try

                -- Get phone numbers
                set phoneList to {{}}
                set phoneDigitsList to {{}}
                try
                    repeat with thePhone in phones of thePerson
                        set phoneValue to value of thePhone as string
                        set end of phoneList to phoneValue
                        -- Extract digits only for search
                        set phoneDigits to do shell script "echo " & quoted form of phoneValue & " | tr -cd '[:digit:]'"
                        set end of phoneDigitsList to phoneDigits
                    end repeat
                on error
                end try

                -- Check search conditions
                if {search_filter} then
                    set contactInfo to "ID:::" & (id of thePerson as string) & "|||"
                    set contactInfo to contactInfo & "Name:::" & fullName & "|||"

                    -- Join emails
                    set AppleScript's text item delimiters to ", "
                    set emailString to emailList as string
                    set AppleScript's text item delimiters to ""
                    set contactInfo to contactInfo & "Emails:::" & emailString & "|||"

                    -- Join phones
                    set AppleScript's text item delimiters to ", "
                    set phoneString to phoneList as string
                    set AppleScript's text item delimiters to ""
                    set contactInfo to contactInfo & "Phones:::" & phoneString & "|||"

                    -- Get organization
                    try
                        set org to organization of thePerson as string
                        if org is not "missing value" then
                            set contactInfo to contactInfo & "Organization:::" & org & "|||"
                        end if
                    on error
                    end try

                    -- Get note
                    try
                        set theNote to note of thePerson as string
                        if theNote is not "missing value" then
                            set contactInfo to contactInfo & "Note:::" & theNote
                        end if
                    on error
                    end try

                    set end of outputList to contactInfo & "<<<CONTACT_END>>>"
                    set contactCount to contactCount + 1
                end if
            end repeat

            return my joinList(outputList, "")
        end tell

        on joinList(lst, delim)
            set AppleScript's text item delimiters to delim
            set txt to lst as text
            set AppleScript's text item delimiters to ""
            return txt
        end joinList
        '''

        result = await applescript_run(script)
        contacts = []

        if result and result != "missing value":
            for contact_data in result.split("<<<CONTACT_END>>>"):
                if contact_data.strip():
                    contact_dict = parse_applescript_record(contact_data.strip())
                    if contact_dict:
                        # Parse emails and phones into lists
                        emails_str = contact_dict.get("Emails", "")
                        contact_dict["Emails"] = [e.strip() for e in emails_str.split(",") if e.strip()]

                        phones_str = contact_dict.get("Phones", "")
                        contact_dict["Phones"] = [p.strip() for p in phones_str.split(",") if p.strip()]

                        contacts.append(contact_dict)

        return contacts

    async def get_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific contact by ID.

        Args:
            contact_id: Contact ID

        Returns:
            Contact dictionary or None if not found
        """
        script = f'''
        tell application "Contacts"
            try
                set thePerson to person id "{contact_id}"

                -- Get contact details
                set fullName to ""
                try
                    set firstName to first name of thePerson as string
                    set lastName to last name of thePerson as string
                    if firstName is "missing value" then set firstName to ""
                    if lastName is "missing value" then set lastName to ""

                    if firstName is not "" and lastName is not "" then
                        set fullName to firstName & " " & lastName
                    else if firstName is not "" then
                        set fullName to firstName
                    else if lastName is not "" then
                        set fullName to lastName
                    else
                        set fullName to "Unknown"
                    end if
                on error
                    set fullName to "Unknown"
                end try

                set contactInfo to "ID:::" & (id of thePerson as string) & "|||"
                set contactInfo to contactInfo & "Name:::" & fullName & "|||"

                -- Get emails
                set emailList to {{}}
                try
                    repeat with theEmail in emails of thePerson
                        set end of emailList to value of theEmail as string
                    end repeat
                on error
                end try

                -- Join emails
                set AppleScript's text item delimiters to ", "
                set emailString to emailList as string
                set AppleScript's text item delimiters to ""
                set contactInfo to contactInfo & "Emails:::" & emailString & "|||"

                -- Get phone numbers
                set phoneList to {{}}
                try
                    repeat with thePhone in phones of thePerson
                        set end of phoneList to value of thePhone as string
                    end repeat
                on error
                end try

                -- Join phones
                set AppleScript's text item delimiters to ", "
                set phoneString to phoneList as string
                set AppleScript's text item delimiters to ""
                set contactInfo to contactInfo & "Phones:::" & phoneString & "|||"

                -- Get address
                try
                    set theAddress to address 1 of thePerson
                    set street to street of theAddress as string
                    set city to city of theAddress as string
                    set state to state of theAddress as string
                    set zip to zip of theAddress as string
                    set addressString to street & ", " & city & ", " & state & " " & zip
                    set contactInfo to contactInfo & "Address:::" & addressString & "|||"
                on error
                end try

                -- Get organization
                try
                    set org to organization of thePerson as string
                    if org is not missing value then
                        set contactInfo to contactInfo & "Organization:::" & org & "|||"
                    end if
                on error
                end try

                -- Get birthday
                try
                    set bday to birth date of thePerson as string
                    if bday is not missing value then
                        set contactInfo to contactInfo & "Birthday:::" & bday & "|||"
                    end if
                on error
                end try

                -- Get note
                try
                    set theNote to note of thePerson as string
                    if theNote is not missing value then
                        set contactInfo to contactInfo & "Note:::" & theNote
                    end if
                on error
                end try

                return contactInfo
            on error
                return "NOT_FOUND"
            end try
        end tell
        '''

        result = await applescript_run(script)

        if result and result.strip() != "NOT_FOUND":
            contact_dict = parse_applescript_record(result.strip())
            if contact_dict:
                # Parse emails and phones into lists
                emails_str = contact_dict.get("Emails", "")
                contact_dict["Emails"] = [e.strip() for e in emails_str.split(",") if e.strip()]

                phones_str = contact_dict.get("Phones", "")
                contact_dict["Phones"] = [p.strip() for p in phones_str.split(",") if p.strip()]

                return contact_dict

        return None

    async def create_contact(
        self,
        first_name: str,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new contact.

        Args:
            first_name: First name
            last_name: Last name (optional)
            email: Email address (optional)
            phone: Phone number (optional)
            organization: Organization/company (optional)
            note: Additional notes (optional)

        Returns:
            Dictionary with creation status and contact details
        """
        properties = [f'first name:"{escape_applescript_string(first_name)}"']

        if last_name:
            properties.append(f'last name:"{escape_applescript_string(last_name)}"')
        if organization:
            properties.append(f'organization:"{escape_applescript_string(organization)}"')
        if note:
            properties.append(f'note:"{escape_applescript_string(note)}"')

        properties_str = "{" + ", ".join(properties) + "}"

        script = f'''
        tell application "Contacts"
            set newPerson to make new person with properties {properties_str}

            {"" if not email else f'make new email at end of emails of newPerson with properties {{label:"work", value:"{email}"}}'}
            {"" if not phone else f'make new phone at end of phones of newPerson with properties {{label:"mobile", value:"{phone}"}}'}

            save

            return "ID:::" & (id of newPerson as string)
        end tell
        '''

        try:
            result = await applescript_run(script)
            contact_info = parse_applescript_record(result)

            return {
                "status": "success",
                "contact_id": contact_info.get("ID", ""),
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "organization": organization
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Convenience functions
async def search_contacts(
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search contacts by name, email, or phone."""
    client = ContactsClient()
    return await client.search_contacts(name, email, phone, limit)


async def get_contact(contact_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific contact by ID."""
    client = ContactsClient()
    return await client.get_contact(contact_id)


async def create_contact(
    first_name: str,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    organization: Optional[str] = None,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new contact."""
    client = ContactsClient()
    return await client.create_contact(first_name, last_name, email, phone, organization, note)