from django.db import connection
from django_test_migrations.contrib.unittest_case import MigratorTestCase


def _delete_tables_postgresql():
    with connection.cursor() as cursor:
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_datacompliance;""")
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_minmaxvalidationrule;""")
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_regularexpressionvalidationrule;""")
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_requiredvalidationrule;""")
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_uniquevalidationrule;""")


def _delete_tables_mysql():
    with connection.cursor() as cursor:
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_datacompliance;""")
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_minmaxvalidationrule;""")
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_regularexpressionvalidationrule;""")
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_requiredvalidationrule;""")
        cursor.execute("""DROP TABLE IF EXISTS nautobot_data_validation_engine_uniquevalidationrule;""")


def _create_tables_postgresql():
    with connection.cursor() as cursor:
        cursor.execute(
            """\
CREATE TABLE nautobot_data_validation_engine_datacompliance (
    id uuid NOT NULL,
    created timestamp with time zone,
    last_updated timestamp with time zone,
    _custom_field_data jsonb NOT NULL,
    compliance_class_name character varying(100) NOT NULL,
    last_validation_date timestamp with time zone NOT NULL,
    object_id character varying(200) NOT NULL,
    validated_object_str character varying(200) NOT NULL,
    validated_attribute character varying(100) NOT NULL,
    validated_attribute_value character varying(200) NOT NULL,
    valid boolean NOT NULL,
    message text NOT NULL,
    content_type_id integer NOT NULL
);"""
        )
        cursor.execute(
            """\
CREATE TABLE nautobot_data_validation_engine_minmaxvalidationrule (
    id uuid NOT NULL,
    created timestamp with time zone,
    last_updated timestamp with time zone,
    name character varying(100) NOT NULL,
    enabled boolean NOT NULL,
    error_message character varying(255) NOT NULL,
    field character varying(50) NOT NULL,
    min double precision,
    max double precision,
    content_type_id integer NOT NULL,
    _custom_field_data jsonb NOT NULL
);"""
        )
        cursor.execute(
            """\
CREATE TABLE nautobot_data_validation_engine_regularexpressionvalidationrule (
    id uuid NOT NULL,
    created timestamp with time zone,
    last_updated timestamp with time zone,
    name character varying(100) NOT NULL,
    enabled boolean NOT NULL,
    error_message character varying(255) NOT NULL,
    field character varying(50) NOT NULL,
    regular_expression text NOT NULL,
    content_type_id integer NOT NULL,
    _custom_field_data jsonb NOT NULL,
    context_processing boolean NOT NULL
);"""
        )
        cursor.execute(
            """\
CREATE TABLE nautobot_data_validation_engine_requiredvalidationrule (
    id uuid NOT NULL,
    created timestamp with time zone,
    last_updated timestamp with time zone,
    _custom_field_data jsonb NOT NULL,
    name character varying(100) NOT NULL,
    enabled boolean NOT NULL,
    error_message character varying(255) NOT NULL,
    field character varying(50) NOT NULL,
    content_type_id integer NOT NULL
);"""
        )
        cursor.execute(
            """\
CREATE TABLE nautobot_data_validation_engine_uniquevalidationrule (
    id uuid NOT NULL,
    created timestamp with time zone,
    last_updated timestamp with time zone,
    _custom_field_data jsonb NOT NULL,
    name character varying(100) NOT NULL,
    enabled boolean NOT NULL,
    error_message character varying(255) NOT NULL,
    field character varying(50) NOT NULL,
    max_instances integer NOT NULL,
    content_type_id integer NOT NULL,
    CONSTRAINT nautobot_data_validation_engine_uniquevalid_max_instances_check CHECK ((max_instances >= 0))
);"""
        )


def _create_tables_mysql():
    with connection.cursor() as cursor:
        cursor.execute(
            """\
CREATE TABLE `nautobot_data_validation_engine_datacompliance` (
  `id` char(32) NOT NULL,
  `created` datetime(6) DEFAULT NULL,
  `last_updated` datetime(6) DEFAULT NULL,
  `_custom_field_data` json NOT NULL,
  `compliance_class_name` varchar(255) NOT NULL,
  `last_validation_date` datetime(6) NOT NULL,
  `object_id` varchar(255) NOT NULL,
  `validated_object_str` varchar(255) NOT NULL,
  `validated_attribute` varchar(255) NOT NULL,
  `validated_attribute_value` varchar(255) NOT NULL,
  `valid` tinyint(1) NOT NULL,
  `message` longtext NOT NULL,
  `content_type_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nautobot_data_validation_compliance_class_name_co_175bd12f_uniq` (`compliance_class_name`,`content_type_id`,`object_id`,`validated_attribute`),
  KEY `nautobot_data_valida_content_type_id_b0211d8e_fk_django_co` (`content_type_id`),
  CONSTRAINT `nautobot_data_valida_content_type_id_b0211d8e_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;"""
        )
        cursor.execute(
            """\
CREATE TABLE `nautobot_data_validation_engine_minmaxvalidationrule` (
  `id` char(32) NOT NULL,
  `created` datetime(6) DEFAULT NULL,
  `last_updated` datetime(6) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `enabled` tinyint(1) NOT NULL,
  `error_message` varchar(255) NOT NULL,
  `field` varchar(50) NOT NULL,
  `min` double DEFAULT NULL,
  `max` double DEFAULT NULL,
  `content_type_id` int NOT NULL,
  `_custom_field_data` json NOT NULL DEFAULT (_utf8mb4'{}'),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `nautobot_data_validation_content_type_id_field_fc531b0c_uniq` (`content_type_id`,`field`),
  CONSTRAINT `nautobot_data_valida_content_type_id_3c749b83_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;"""
        )
        cursor.execute(
            """\
CREATE TABLE `nautobot_data_validation_engine_regularexpressionvalidationrule` (
  `id` char(32) NOT NULL,
  `created` datetime(6) DEFAULT NULL,
  `last_updated` datetime(6) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `enabled` tinyint(1) NOT NULL,
  `error_message` varchar(255) NOT NULL,
  `field` varchar(50) NOT NULL,
  `regular_expression` longtext NOT NULL,
  `content_type_id` int NOT NULL,
  `_custom_field_data` json NOT NULL DEFAULT (_utf8mb4'{}'),
  `context_processing` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `nautobot_data_validation_content_type_id_field_35add806_uniq` (`content_type_id`,`field`),
  CONSTRAINT `nautobot_data_valida_content_type_id_b863523b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;"""
        )
        cursor.execute(
            """\
CREATE TABLE `nautobot_data_validation_engine_requiredvalidationrule` (
  `id` char(32) NOT NULL,
  `created` datetime(6) DEFAULT NULL,
  `last_updated` datetime(6) DEFAULT NULL,
  `_custom_field_data` json NOT NULL,
  `name` varchar(100) NOT NULL,
  `enabled` tinyint(1) NOT NULL,
  `error_message` varchar(255) NOT NULL,
  `field` varchar(50) NOT NULL,
  `content_type_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `nautobot_data_validation_content_type_id_field_c7aa1e2a_uniq` (`content_type_id`,`field`),
  CONSTRAINT `nautobot_data_valida_content_type_id_1a017307_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;"""
        )
        cursor.execute(
            """\
CREATE TABLE `nautobot_data_validation_engine_uniquevalidationrule` (
  `id` char(32) NOT NULL,
  `created` datetime(6) DEFAULT NULL,
  `last_updated` datetime(6) DEFAULT NULL,
  `_custom_field_data` json NOT NULL,
  `name` varchar(100) NOT NULL,
  `enabled` tinyint(1) NOT NULL,
  `error_message` varchar(255) NOT NULL,
  `field` varchar(50) NOT NULL,
  `max_instances` int unsigned NOT NULL,
  `content_type_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `nautobot_data_validation_content_type_id_field_bacfb976_uniq` (`content_type_id`,`field`),
  CONSTRAINT `nautobot_data_valida_content_type_id_d195eaeb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `nautobot_data_validation_engine_uniquevalidationrule_chk_1` CHECK ((`max_instances` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;"""
        )


def _populate_tables_postgresql(ContentType, DeviceType, VLAN):
    with connection.cursor() as cursor:
        cursor.execute(
            """\
INSERT INTO nautobot_data_validation_engine_datacompliance
VALUES (
  'f20e4572-84cf-4f28-9fe6-5f0f96f78d14',
  '2025-10-21 16:07:55.123456+00',
  '2025-10-21 16:07:55.123456+00',
  '{}',
  'DcimDevicetypeCustomValidator',
  '2025-10-21 16:07:55.123456+00',
  '96591cd4-c4d1-4d69-982d-195bcea71a2c',
  'Juniper SRX300',
  'part_number',
  '',
  'f',
  'A device type may only contain alpha numeric, dashes, and underscore characters.',
  %s
);""",
            [ContentType.objects.get_for_model(DeviceType).id],
        )

        # Min/max validation rules
        cursor.execute(
            """\
INSERT INTO nautobot_data_validation_engine_minmaxvalidationrule
VALUES (
  '57f06495-503e-5202-8ce3-ccba5acc8ecc',
  '2025-03-11 15:35:28.260978+00',
  '2025-03-11 15:35:28.260996+00',
  'Max VLAN ID',
  'f',
  '',
  'vid',
  NULL,
  3999,
  %s,
  '{}'
);""",
            [ContentType.objects.get_for_model(VLAN).id],
        )
        # Regular Expression validation rules
        cursor.execute(
            """\
INSERT INTO nautobot_data_validation_engine_regularexpressionvalidationrule
VALUES (
  '0f8a822b-36cd-58f3-804a-825541896855',
  '2025-03-11 15:35:28.215025+00',
  '2025-03-11 15:35:28.215041+00',
  'Device Type Part Number',
  't',
  'A device type may only contain alpha numeric, dashes, and underscore characters.',
  'part_number',
  '^[a-zA-Z0-9_-]+$',
  %s,
  '{}',
  'f'
), (
  'ffdc62b7-c73e-51b9-a464-0240dc20c40b',
  '2025-03-11 15:35:28.242279+00',
  '2025-03-11 15:35:28.242296+00',
  'Device Type Part Model',
  't',
  'A device type may only contain alpha numeric, dashes, and underscore characters.',
  'model',
  '^[a-zA-Z0-9_-]+$',
  %s,
  '{}',
  'f'
);""",
            [ContentType.objects.get_for_model(DeviceType).id, ContentType.objects.get_for_model(DeviceType).id],
        )

        # TODO: requiredvalidationrule
        # TODO: uniquevalidationrule


def _populate_tables_mysql(ContentType, DeviceType, VLAN):
    with connection.cursor() as cursor:
        cursor.execute(
            """\
INSERT INTO `nautobot_data_validation_engine_datacompliance`
VALUES (
  'f20e457284cf4f289fe65f0f96f78d14',
  '2025-10-21 16:07:55.123456',
  '2025-10-21 16:07:55.123456',
  '{}',
  'DcimDevicetypeCustomValidator',
  '2025-10-21 16:07:55.123456',
  '96591cd4c4d14d69982d195bcea71a2c',
  'Juniper SRX300',
  'part_number',
  '',
  0,
  'A device type may only contain alpha numeric, dashes, and underscore characters.',
  %s
);""",
            [ContentType.objects.get_for_model(DeviceType).id],
        )

        # Min/max validation rules
        cursor.execute(
            """\
INSERT INTO `nautobot_data_validation_engine_minmaxvalidationrule`
VALUES (
  '57f06495503e52028ce3ccba5acc8ecc',
  '2025-04-21 21:17:01.643525',
  '2025-04-21 21:17:01.643566',
  'Max VLAN ID',
  0,
  '',
  'vid',
  NULL,
  3999,
  %s,
  '{}'
);""",
            [ContentType.objects.get_for_model(VLAN).id],
        )

        # Regular Expression validation rules
        cursor.execute(
            """\
INSERT INTO `nautobot_data_validation_engine_regularexpressionvalidationrule`
VALUES (
    '0f8a822b36cd58f3804a825541896855',
    '2025-04-21 21:17:01.581491',
    '2025-04-21 21:17:01.581523',
    'Device Type Part Number',
    1,
    'A device type may only contain alpha numeric, dashes, and underscore characters.',
    'part_number',
    '^[a-zA-Z0-9_-]+$',
    %s,
    '{}',
    0
),(
    'ffdc62b7c73e51b9a4640240dc20c40b',
    '2025-04-21 21:17:01.615285',
    '2025-04-21 21:17:01.615314',
    'Device Type Part Model',
    1,
    'A device type may only contain alpha numeric, dashes, and underscore characters.',
    'model',
    '^[a-zA-Z0-9_-]+$',
    %s,
    '{}',
    0
);""",
            [ContentType.objects.get_for_model(DeviceType).id, ContentType.objects.get_for_model(DeviceType).id],
        )

        # TODO: requiredvalidationrule
        # TODO: uniquevalidationrule


class DVEToDataValidationMigrationTestCase(MigratorTestCase):
    """Test data migrations migrating the Data Validation Engine App into Nautobot core."""

    migrate_from = ("data_validation", "0001_initial")
    migrate_to = ("data_validation", "0002_data_migration_from_app")

    def prepare(self):
        """Populate data-validation-engine tables."""
        ContentType = self.old_state.apps.get_model("contenttypes", "contenttype")
        DeviceType = self.old_state.apps.get_model("dcim", "devicetype")
        VLAN = self.old_state.apps.get_model("ipam", "vlan")
        if connection.vendor == "postgresql":
            _delete_tables_postgresql()
            _create_tables_postgresql()
            _populate_tables_postgresql(ContentType, DeviceType, VLAN)
        elif connection.vendor == "mysql":
            _delete_tables_mysql()
            _create_tables_mysql()
            _populate_tables_mysql(ContentType, DeviceType, VLAN)
        else:
            raise ValueError(f"Unknown/unsupported database vendor {connection.vendor}")

    def tearDown(self):
        super().tearDown()
        if connection.vendor == "postgresql":
            _delete_tables_postgresql()
        elif connection.vendor == "mysql":
            _delete_tables_mysql()

    def test_validate_data(self):
        DataCompliance = self.new_state.apps.get_model("data_validation", "datacompliance")
        MinMaxValidationRule = self.new_state.apps.get_model("data_validation", "minmaxvalidationrule")
        RegularExpressionValidationRule = self.new_state.apps.get_model(
            "data_validation", "regularexpressionvalidationrule"
        )
        RequiredValidationRule = self.new_state.apps.get_model("data_validation", "requiredvalidationrule")
        UniqueValidationRule = self.new_state.apps.get_model("data_validation", "uniquevalidationrule")

        with self.subTest("DataCompliance"):
            self.assertEqual(DataCompliance.objects.count(), 1)

        with self.subTest("MinMaxValidationRule"):
            self.assertEqual(MinMaxValidationRule.objects.count(), 1)

        with self.subTest("RegularExpressionValidationRule"):
            self.assertEqual(RegularExpressionValidationRule.objects.count(), 2)

        with self.subTest("RequiredValidationRule"):
            self.assertEqual(RequiredValidationRule.objects.count(), 0)

        with self.subTest("UniqueValidationRule"):
            self.assertEqual(UniqueValidationRule.objects.count(), 0)


class DataValidationToDVEMigrationTestCase(MigratorTestCase):
    """Test reverse data migrations migrating the Data Validation Engine App out of Nautobot core."""

    migrate_to = ("data_validation", "0002_data_migration_from_app")
    migrate_from = ("data_validation", "0001_initial")

    def prepare(self):
        if connection.vendor == "postgresql":
            _delete_tables_postgresql()
            _create_tables_postgresql()
        elif connection.vendor == "mysql":
            _delete_tables_mysql()
            _create_tables_mysql()
        else:
            raise ValueError(f"Unknown/unsupported database vendor {connection.vendor}")

        ContentType = self.old_state.apps.get_model("contenttypes", "contenttype")
        DeviceType = self.old_state.apps.get_model("dcim", "devicetype")
        VLAN = self.old_state.apps.get_model("ipam", "vlan")

        DataCompliance = self.old_state.apps.get_model("data_validation", "datacompliance")
        MinMaxValidationRule = self.old_state.apps.get_model("data_validation", "minmaxvalidationrule")
        RegularExpressionValidationRule = self.old_state.apps.get_model(
            "data_validation", "regularexpressionvalidationrule"
        )

        DataCompliance.objects.create(
            compliance_class_name="DcimDevicetypeCustomValidator",
            object_id="96591cd4-c4d1-4d69-982d-195bcea71a2c",
            validated_object_str="Juniper SRX300",
            validated_attribute="part_number",
            validated_attribute_value="",
            valid=False,
            message="A device type may only contain alpha numeric, dashes, and underscore characters.",
            content_type=ContentType.objects.get_for_model(DeviceType),
        )
        MinMaxValidationRule.objects.create(
            name="Max VLAN ID",
            enabled=False,
            error_message="",
            field="vid",
            min=None,
            max=3999,
            content_type=ContentType.objects.get_for_model(VLAN),
        )
        RegularExpressionValidationRule.objects.create(
            name="Device Type Part Number",
            enabled=True,
            error_message="A device type may only contain alpha numeric, dashes, and underscore characters.",
            field="part_number",
            regular_expression="^[a-zA-Z0-9_-]+$",
            content_type=ContentType.objects.get_for_model(DeviceType),
            context_processing=False,
        )

        # TODO: requiredvalidationrule
        # TODO: uniquevalidationrule

    def tearDown(self):
        super().tearDown()
        if connection.vendor == "postgresql":
            _delete_tables_postgresql()
        elif connection.vendor == "mysql":
            _delete_tables_mysql()

    def test_validate_data(self):
        # Just the fact that the reverse migration succeeds at all is evidence enough for now
        pass
