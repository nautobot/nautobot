from django.db import migrations

POSTGRES_CREATE = r"""
CREATE OR REPLACE FUNCTION bytea_to_ip_string(ip bytea) RETURNS text AS $$
BEGIN
  -- IPv4: 4 bytes -> dotted decimal
  IF length(ip) = 4 THEN
    RETURN
      get_byte(ip, 0)::text || '.' ||
      get_byte(ip, 1)::text || '.' ||
      get_byte(ip, 2)::text || '.' ||
      get_byte(ip, 3)::text;

  -- IPv6: 16 bytes -> compressed canonical form using inet
  ELSIF length(ip) = 16 THEN
    RETURN (
      format(
        '%s:%s:%s:%s:%s:%s:%s:%s',
        lpad(to_hex(get_byte(ip, 0)), 2, '0') || lpad(to_hex(get_byte(ip, 1)), 2, '0'),
        lpad(to_hex(get_byte(ip, 2)), 2, '0') || lpad(to_hex(get_byte(ip, 3)), 2, '0'),
        lpad(to_hex(get_byte(ip, 4)), 2, '0') || lpad(to_hex(get_byte(ip, 5)), 2, '0'),
        lpad(to_hex(get_byte(ip, 6)), 2, '0') || lpad(to_hex(get_byte(ip, 7)), 2, '0'),
        lpad(to_hex(get_byte(ip, 8)), 2, '0') || lpad(to_hex(get_byte(ip, 9)), 2, '0'),
        lpad(to_hex(get_byte(ip,10)), 2, '0') || lpad(to_hex(get_byte(ip,11)), 2, '0'),
        lpad(to_hex(get_byte(ip,12)), 2, '0') || lpad(to_hex(get_byte(ip,13)), 2, '0'),
        lpad(to_hex(get_byte(ip,14)), 2, '0') || lpad(to_hex(get_byte(ip,15)), 2, '0')
      )::inet
    )::text;

  ELSE
    RETURN NULL;
  END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

POSTGRES_DROP = "DROP FUNCTION IF EXISTS bytea_to_ip_string(bytea);"


MYSQL_CREATE = r"""
CREATE FUNCTION bytea_to_ip_string(ip VARBINARY(16)) RETURNS VARCHAR(45)
DETERMINISTIC
BEGIN
  DECLARE len INT;
  SET len = OCTET_LENGTH(ip);

  -- IPv4: 4 bytes -> dotted decimal
  IF len = 4 THEN
    RETURN CONCAT(
      CONV(HEX(SUBSTRING(ip, 1, 1)), 16, 10), '.',
      CONV(HEX(SUBSTRING(ip, 2, 1)), 16, 10), '.',
      CONV(HEX(SUBSTRING(ip, 3, 1)), 16, 10), '.',
      CONV(HEX(SUBSTRING(ip, 4, 1)), 16, 10)
    );

  -- IPv6: 16 bytes -> canonical printable form
  ELSEIF len = 16 THEN
    -- Assumes ip is stored in INET6_ATON-compatible format
    RETURN INET6_NTOA(ip);

  ELSE
    RETURN NULL;
  END IF;
END;
"""

MYSQL_DROP = "DROP FUNCTION IF EXISTS bytea_to_ip_string;"


def forwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    with schema_editor.connection.cursor() as cursor:
        if vendor == "postgresql":
            cursor.execute(POSTGRES_CREATE)
        elif vendor == "mysql":
            cursor.execute(MYSQL_CREATE)
        else:
            pass


def backwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    with schema_editor.connection.cursor() as cursor:
        if vendor == "postgresql":
            cursor.execute(POSTGRES_DROP)
        elif vendor == "mysql":
            cursor.execute(MYSQL_DROP)
        else:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ("ipam", "0054_namespace_tenant"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
