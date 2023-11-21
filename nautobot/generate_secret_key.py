#!/usr/bin/env python
# This script will generate a random 50-character string suitable for use as a SECRET_KEY.
# shamelessly pulled from https://docs.python.org/3/library/secrets.html#recipes-and-best-practices
import string
import secrets

length = 50
alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"  # string.punctuation would be an option
while True:
    password = "".join(secrets.choice(alphabet) for i in range(length))
    if (
        any(c.islower() for c in password)
        and any(c.isupper() for c in password)
        and sum(c.isdigit() for c in password) >= 3
    ):
        break
print(password)
