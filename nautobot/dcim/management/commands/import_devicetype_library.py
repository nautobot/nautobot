import glob

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, transaction
import yaml

from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models.device_component_templates import (
    ConsolePortTemplate,
    ConsoleServerPortTemplate,
    DeviceBayTemplate,
    FrontPortTemplate,
    InterfaceTemplate,
    PowerOutletTemplate,
    PowerPortTemplate,
    RearPortTemplate,
)
from nautobot.dcim.models.devices import DeviceType, Manufacturer


class Command(BaseCommand):
    help = "Installs the device type library fixture(s) in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='Nominates a specific database to load fixtures into. Defaults to the "default" database.',
        )
        parser.add_argument(
            "--dtl-path",
            help="Path to the devicetype-library/device-types directory.",
        )

    def handle(self, *args, **options):
        self.using = options["database"]
        created_objects = {
            "manufacturer": 0,
            "device_type": 0,
            "console_port_template": 0,
            "console_server_port_template": 0,
            "device_bay_template": 0,
            "front_port_template": 0,
            "interface_template": 0,
            "inventory_item_template": 0,
            "module_bay_template": 0,
            "power_outlet_template": 0,
            "power_port_template": 0,
            "rear_port_template": 0,
        }
        for dtl_file in glob.iglob(options["dtl_path"] + "**/*.yaml", recursive=True):
            with open(dtl_file, "rb") as f:
                dtl = yaml.safe_load(f)
                with transaction.atomic():
                    mfr, created = Manufacturer.objects.get_or_create(name=dtl["manufacturer"])
                    created_objects["manufacturer"] += int(created)

                    # create device type
                    #   netbox has an "airflow" field that nautobot does not support
                    #   netbox has a "description" field that nautobot does not support
                    #   netbox has an "is_powered" boolean field that nautobot does not support
                    #   netbox has a "slug" field that nautobot does not support
                    #   netbox has a "subdevice_role" field that nautobot does not support
                    #   netbox has "weight" and "weight_unit" fields that nautobot does not support
                    dt, created = DeviceType.objects.get_or_create(
                        manufacturer=mfr,
                        model=dtl["model"],
                        defaults={
                            "comments": dtl.get("comments", ""),
                            "is_full_depth": dtl.get("is_full_depth", True),
                            "part_number": dtl.get("part_number", ""),
                            "u_height": dtl.get("u_height", 1),
                        },
                    )
                    created_objects["device_type"] += int(created)

                    # create related console-port template
                    #   all ConsolePort types match between netbox/nautobot
                    #   netbox has a "poe" boolean field that nautobot does not support
                    for console_port in dtl.get("console-ports", []):
                        _, created = ConsolePortTemplate.objects.get_or_create(
                            device_type=dt,
                            name=console_port["name"],
                            defaults={
                                "type": console_port.get("type", ""),
                                "label": console_port.get("label", ""),
                                "description": console_port.get("description", ""),
                            },
                        )
                        created_objects["console_port_template"] += int(created)

                    # create related console-server-port template
                    #   all ConsoleServerPort types match between netbox/nautobot
                    for console_server_port in dtl.get("console-server-ports", []):
                        _, created = ConsoleServerPortTemplate.objects.get_or_create(
                            device_type=dt,
                            name=console_server_port["name"],
                            defaults={
                                "type": console_server_port.get("type", ""),
                                "label": console_server_port.get("label", ""),
                            },
                        )
                        created_objects["console_server_port_template"] += int(created)

                    # create related device-bay template
                    for device_bay in dtl.get("device-bays", []):
                        _, created = DeviceBayTemplate.objects.get_or_create(
                            device_type=dt,
                            name=device_bay["name"],
                            defaults={
                                "label": device_bay.get("label", ""),
                            },
                        )
                        created_objects["device_bay_template"] += int(created)

                    # create related rear-port template
                    #   netbox has a "color" field that nautobot does not support
                    #   netbox has a "poe" boolean field that nautobot does not support
                    #   extra netbox PortTypeChoices: lx5,lx5-pc,lx5-upc,lx5-apc
                    for rear_port in dtl.get("rear-ports", []):
                        _, created = RearPortTemplate.objects.get_or_create(
                            device_type=dt,
                            name=rear_port["name"],
                            defaults={
                                "type": rear_port.get("type", ""),
                                "positions": rear_port.get("positions", 1),
                                "label": rear_port.get("label", ""),
                                "description": rear_port.get("description", ""),
                            },
                        )
                        created_objects["rear_port_template"] += int(created)

                    # create related front-port template
                    #   netbox has a "color" field that nautobot does not support
                    #   extra netbox PortTypeChoices: lx5,lx5-pc,lx5-upc,lx5-apc
                    for front_port in dtl.get("front-ports", []):
                        rear_port = None
                        if front_port.get("rear_port", ""):
                            rear_port = RearPortTemplate.objects.filter(
                                device_type=dt, name=front_port["rear_port"]
                            ).first()
                            if rear_port is None:
                                self.stderr.write(
                                    self.style.ERROR(
                                        f"Rear port {front_port['rear_port']} not found for front port: "
                                        f"Manufacturer '{dtl['manufacturer']}' - Model '{dtl['model']}' - "
                                        f"Front Port '{front_port['name']}'."
                                    )
                                )
                                continue
                        _, created = FrontPortTemplate.objects.get_or_create(
                            device_type=dt,
                            name=front_port["name"],
                            defaults={
                                "type": front_port.get("type", ""),
                                "rear_port_template": rear_port,
                                "rear_port_position": front_port.get("rear_port_position", 1),
                                "label": front_port.get("label", ""),
                                "description": front_port.get("description", ""),
                            },
                        )
                        created_objects["front_port_template"] += int(created)

                    # create related interface template
                    #   netbox has a "poe_mode" field that nautobot does not support
                    #   netbox has a "poe_type" field that nautobot does not support
                    #   type mismatches not checked, there are inevitable differences
                    for interface in dtl.get("interfaces", []):
                        type_ = interface.get("type", "")
                        if type_ not in InterfaceTypeChoices.values():
                            self.stderr.write(
                                self.style.ERROR(
                                    f"Interface type {type_} not found for interface: "
                                    f"Manufacturer '{dtl['manufacturer']}' - Model '{dtl['model']}' - "
                                    f"Interface '{interface['name']}'."
                                )
                            )
                            type_ = "other"

                        _, created = InterfaceTemplate.objects.get_or_create(
                            device_type=dt,
                            name=interface["name"],
                            defaults={
                                "type": type_,
                                "mgmt_only": interface.get("mgmt_only", False),
                                "label": interface.get("label", ""),
                                "description": interface.get("description", ""),
                            },
                        )
                        created_objects["interface_template"] += int(created)

                    # create related power-port template
                    #   extra netbox PowerPortTypeChoices: iec-60906-1,nbr-14136-10a,nbr-14136-20a
                    for pp in dtl.get("power-ports", []):
                        _, created = PowerPortTemplate.objects.get_or_create(
                            device_type=dt,
                            name=pp["name"],
                            defaults={
                                "type": pp.get("type", ""),
                                "maximum_draw": pp.get("maximum_draw", None),
                                "allocated_draw": pp.get("allocated_draw", None),
                                "label": pp.get("label", ""),
                            },
                        )
                        created_objects["power_port_template"] += int(created)

                    # create related power-outlet template
                    #   extra netbox PowerOutletTypeChoices: iec-60906-1,nbr-14136-10a,nbr-14136-20a
                    for power_outlet in dtl.get("power-outlets", []):
                        power_port = None
                        if power_outlet.get("power_port", ""):
                            power_port = PowerPortTemplate.objects.filter(
                                device_type=dt, name=power_outlet["power_port"]
                            ).first()
                            if power_port is None:
                                self.stderr.write(
                                    self.style.ERROR(
                                        f"Power port {power_outlet['power_port']} not found for power outlet: "
                                        f"Manufacturer '{dtl['manufacturer']}' - Model '{dtl['model']}' - "
                                        f"Power Outlet '{power_outlet['name']}'."
                                    )
                                )
                                continue
                        _, created = PowerOutletTemplate.objects.get_or_create(
                            device_type=dt,
                            name=power_outlet["name"],
                            defaults={
                                "type": power_outlet.get("type", ""),
                                "feed_leg": power_outlet.get("feed_leg", ""),
                                "power_port_template": power_port,
                                "label": power_outlet.get("label", ""),
                            },
                        )
                        created_objects["power_outlet_template"] += int(created)

                    # TODO: create related inventory-item template - nautobot does not support these yet
                    # for inventory_item in dtl.get("inventory-items", []):
                    #     pass

                    # TODO: create related module-bay template - pending nautobot module bay model
                    # for module_bay in dtl.get("module-bays", []):
                    #     pass

                    # TODO: create front_image and rear_image

        for name, count in created_objects.items():
            self.stdout.write(f"Created {count} {name}s.")
