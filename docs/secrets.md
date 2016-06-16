<h1>Secrets</h1>

"Secrets" are small amounts of data that must be kept confidential; for example, passwords and SNMP community strings. NetBox provides encrypted storage of secret data.

[TOC]

# Secrets

A secret represents a single credential or other string which must be stored securely. Each secret is assigned to a device within NetBox. The plaintext value of a secret is encrypted to a ciphertext immediately prior to storage within the database using a 256-bit AES master key. A SHA256 hash of the plaintext is also stored along with each ciphertext to validate the decrypted plaintext.

Each secret can also store an optional name parameter, which is not encrypted. This may be useful for storing user names.

### Roles

Each secret is assigned a functional role which indicates what it is used for. Typical roles might include:

* Login credentials
* SNMP community strings
* RADIUS/TACACS+ keys
* IKE key strings
* Routing protocol shared secrets

---

# User Keys

Each user within NetBox can associate his or her account with an RSA public key. If activated by an administrator, this user key will contain a unique, encrypted copy of the AES master key needed to retrieve secret data.

User keys may be created by users individually, however they are of no use until they have been activated by a user who already has access to retrieve secret data.
