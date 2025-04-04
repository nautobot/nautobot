-- Allow the nautobot user to create databases, this is required to run unittests
GRANT ALL PRIVILEGES ON *.* TO 'nautobot'@'%';
