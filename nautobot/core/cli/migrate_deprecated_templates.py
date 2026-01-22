import argparse
import os
import re

TEMPLATE_REPLACEMENTS = {
    # Format: new_template: [old_template1, old_template2, ...]
    "circuits/circuit_create.html": ["circuits/circuit_edit.html", "circuits/circuit_update.html"],
    "circuits/circuittermination_create.html": [
        "circuits/circuittermination_edit.html",
        "circuits/circuittermination_update.html",
    ],
    "circuits/provider_create.html": ["circuits/provider_edit.html", "circuits/provider_update.html"],
    "dcim/cable_retrieve.html": ["dcim/cable.html"],
    "dcim/cable_update.html": ["dcim/cable_edit.html"],
    "dcim/device_create.html": ["dcim/device_edit.html"],
    "dcim/devicetype_update.html": ["dcim/devicetype_edit.html"],
    "dcim/location_update.html": ["dcim/location_edit.html"],
    "dcim/rack_retrieve.html": ["dcim/rack.html"],
    "dcim/rack_update.html": ["dcim/rack_edit.html"],
    "dcim/rackreservation_retrieve.html": ["dcim/rackreservation.html"],
    "dcim/virtualchassis_create.html": ["dcim/virtualchassis_add.html"],
    "extras/configcontext_update.html": ["extras/configcontext_edit.html"],
    "extras/configcontextschema_retrieve.html": ["extras/configcontextschema.html"],
    "extras/configcontextschema_update.html": ["extras/configcontextschema_edit.html"],
    "extras/customfield_update.html": ["extras/customfield_edit.html"],
    "extras/dynamicgroup_retrieve.html": ["extras/dynamicgroup.html"],
    "extras/dynamicgroup_update.html": ["extras/dynamicgroup_edit.html"],
    "extras/gitrepository_retrieve.html": ["extras/gitrepository.html"],
    "extras/gitrepository_update.html": ["extras/gitrepository_object_edit.html"],
    "extras/jobresult_retrieve.html": ["extras/jobresult.html"],
    "extras/objectchange_retrieve.html": ["extras/objectchange.html"],
    "extras/secret_create.html": ["extras/secret_edit.html"],
    "extras/secretsgroup_update.html": ["extras/secretsgroup_edit.html"],
    "extras/tag_update.html": ["extras/tag_edit.html"],
    "generic/object_bulk_create.html": ["generic/object_bulk_import.html"],
    "generic/object_bulk_destroy.html": ["generic/object_bulk_delete.html"],
    "generic/object_bulk_update.html": ["generic/object_bulk_edit.html"],
    "generic/object_changelog.html": ["extras/object_changelog.html"],
    "generic/object_create.html": ["dcim/powerpanel_edit.html", "generic/object_edit.html", "ipam/service_edit.html"],
    "generic/object_destroy.html": ["generic/object_delete.html"],
    "generic/object_list.html": ["extras/graphqlquery_list.html", "extras/objectchange_list.html"],
    "generic/object_notes.html": ["extras/object_notes.html"],
    "generic/object_retrieve.html": [
        "circuits/circuit.html",
        "circuits/circuit_retrieve.html",
        "circuits/circuittermination.html",
        "circuits/circuittermination_retrieve.html",
        "circuits/circuittype.html",
        "circuits/circuittype_retrieve.html",
        "circuits/provider.html",
        "circuits/provider_retrieve.html",
        "circuits/providernetwork.html",
        "circuits/providernetwork_retrieve.html",
        "cloud/cloudaccount_retrieve.html",
        "cloud/cloudnetwork_retrieve.html",
        "cloud/cloudresourcetype_retrieve.html",
        "cloud/cloudservice_retrieve.html",
        "dcim/controller/base.html",
        "dcim/controller_retrieve.html",
        "dcim/controller_wirelessnetworks.html",
        "dcim/controllermanageddevicegroup_retrieve.html",
        "dcim/device/base.html",
        "dcim/device/consoleports.html",
        "dcim/device/consoleserverports.html",
        "dcim/device/devicebays.html",
        "dcim/device/frontports.html",
        "dcim/device/interfaces.html",
        "dcim/device/inventory.html",
        "dcim/device/modulebays.html",
        "dcim/device/poweroutlets.html",
        "dcim/device/powerports.html",
        "dcim/device/rearports.html",
        "dcim/device/wireless.html",
        "dcim/device_component.html",
        "dcim/devicefamily_retrieve.html",
        "dcim/deviceredundancygroup_retrieve.html",
        "dcim/devicetype.html",
        "dcim/devicetype_retrieve.html",
        "dcim/interfaceredundancygroup_retrieve.html",
        "dcim/location.html",
        "dcim/location_retrieve.html",
        "dcim/locationtype.html",
        "dcim/locationtype_retrieve.html",
        "dcim/manufacturer.html",
        "dcim/modulebay_retrieve.html",
        "dcim/platform.html",
        "dcim/powerfeed.html",
        "dcim/powerfeed_retrieve.html",
        "dcim/powerpanel.html",
        "dcim/powerpanel_retrieve.html",
        "dcim/rackgroup.html",
        "dcim/softwareimagefile_retrieve.html",
        "dcim/softwareversion_retrieve.html",
        "dcim/virtualchassis.html",
        "dcim/virtualchassis_retrieve.html",
        "dcim/virtualdevicecontext_retrieve.html",
        "extras/computedfield.html",
        "extras/computedfield_retrieve.html",
        "extras/configcontext.html",
        "extras/configcontext_retrieve.html",
        "extras/contact_retrieve.html",
        "extras/customfield.html",
        "extras/customfield_retrieve.html",
        "extras/customlink.html",
        "extras/exporttemplate.html",
        "extras/graphqlquery.html",
        "extras/graphqlquery_retrieve.html",
        "extras/job_detail.html",
        "extras/jobbutton_retrieve.html",
        "extras/jobhook.html",
        "extras/jobqueue_retrieve.html",
        "extras/metadatatype_retrieve.html",
        "extras/note.html",
        "extras/note_retrieve.html",
        "extras/relationship.html",
        "extras/secret.html",
        "extras/secretsgroup.html",
        "extras/secretsgroup_retrieve.html",
        "extras/status.html",
        "extras/tag.html",
        "extras/tag_retrieve.html",
        "extras/team_retrieve.html",
        "generic/object_detail.html",
        "ipam/namespace_retrieve.html",
        "ipam/prefix.html",
        "ipam/prefix_retrieve.html",
        "ipam/rir.html",
        "ipam/routetarget.html",
        "ipam/service.html",
        "ipam/service_retrieve.html",
        "ipam/vlan.html",
        "ipam/vlan_retrieve.html",
        "ipam/vlangroup.html",
        "ipam/vrf.html",
        "tenancy/tenant.html",
        "tenancy/tenantgroup.html",
        "tenancy/tenantgroup_retrieve.html",
        "virtualization/clustergroup.html",
        "virtualization/clustertype.html",
        "virtualization/virtualmachine.html",
        "virtualization/virtualmachine_retrieve.html",
        "wireless/radioprofile_retrieve.html",
        "wireless/supporteddatarate_retrieve.html",
        "wireless/wirelessnetwork_retrieve.html",
    ],
    "ipam/prefix_create.html": ["ipam/prefix_edit.html"],
    "ipam/vlan_update.html": ["ipam/vlan_edit.html"],
    "tenancy/tenant_create.html": ["tenancy/tenant_edit.html"],
    "virtualchassis_update.html": ["dcim/virtualchassis_edit.html"],
    "virtualization/virtualmachine_update.html": ["virtualization/virtualmachine_edit.html"],
}


def replace_template_references(content: str) -> tuple[str, bool]:
    """
    Replaces references to deprecated templates with new ones.

    Args:
        content: The content of the file to replace references in.

    Returns:
        A tuple containing the updated content and a boolean indicating if any changes were made.
    """
    for new_template, old_templates in TEMPLATE_REPLACEMENTS.items():
        for old_template in old_templates:
            pattern = rf"(\{{%\s*extends\s*['\"]){re.escape(old_template)}(['\"]\s*%\}})"
            new_content, count = re.subn(pattern, rf"\1{new_template}\2", content)
            if count > 0:
                # A django template can only have one extends statement, so we can return as soon as we find a match.
                return new_content, True

    return content, False


def replace_deprecated_templates(path: str, dry_run: bool = False):
    """
    Recursively finds all .html files in the given directory,
    and replaces references to deprecated templates with new ones.
    """

    if os.path.isfile(path):
        only_filename = os.path.basename(path)
        path = os.path.dirname(path)
    else:
        only_filename = None
    print("Finding deprecated templates to replace...")
    count = 0

    for root, _, files in os.walk(path):
        for filename in files:
            if only_filename and only_filename != filename:
                continue
            if filename.endswith((".html")):
                file_path = os.path.join(root, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    original_content = f.read()

                content = original_content

                fixed_content, was_updated = replace_template_references(content)

                if was_updated:
                    count += 1
                    if dry_run:
                        print(f"Detected deprecated template reference in {file_path}")
                        continue
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)
                    print(f"Updated: {file_path}")
    if not count:
        print("No deprecated templates found.")
    else:
        print(f"Found {count} deprecated templates.")
    return count


def main():
    parser = argparse.ArgumentParser(description="Replace deprecated templates with new ones")
    parser.add_argument("path", type=str, help="Path to directory in which to recursively fix all .html files.")
    parser.add_argument("--dry-run", action="store_true", help="Do not make any changes to the files.")
    args = parser.parse_args()

    replace_deprecated_templates(args.path, args.dry_run)


if __name__ == "__main__":
    main()
