#!/usr/bin/env python
# This script will generate a random 50-character string suitable for use as a SECRET_KEY.
from random import SystemRandom

choice = SystemRandom().choice

charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*(-_=+)"
print("".join(choice(charset) for _ in range(50)))
