# phish-email-anonymizer

This project develops an anonymizer for phishing emails. The input are emails in JSON
format in an input folder. The output are anonymized emails with From, To, Subject
and body of the email, in an output folder, as plain text.

Emails can be transformed from EML to JSON using code at
https://gitlab.com/isi-piranha/tools/eml-munging-toolkit

Anonymizer will do the following:
- keep only content=text/plain parts of email
- keep from, to and subject from email header
- detect personal names and change them to other random names (gender is not preserved)
- detect locations and change them to AnonCity, AnonState, etc.
- detect phone numbers and change them to random phone numbers (10-digit, not guaranteed to be valid)
- detect email usernames and change them to random usernames in accordance to personal name changes
- detect email domains and change them ONLY if they belong to USC
- detect URLs and crop them to only keep the domain

Install anaconda

Use environment.yml to start a virtual environment for Python like conda env create -f environment.yml

Run code as:
    python anonymizer.py <input-folder> <output-folder>
