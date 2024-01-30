# Software Image

+++ 2.2.0
    This model will replace the `SoftwareImageLCM` model from [Nautobot Device Lifecycle Management](https://docs.nautobot.com/projects/device-lifecycle/en/latest/)

A software image represents a single file, typically the installation image, used to run or install a device or virtual machine's operating system. Device and virtual machines can optionally assign a software image for tracking the current image in use. Device types and inventory items can be assigned to multiple software images to track which images are compatible with which device types or inventory items. Software images are related to [software versions](softwareversion.md) which are used to track attributes that may apply to multiple software images, such as the end of support date or security vulnerabilities that affect that version.

A software image must include a file name and a related [software version](softwareversion.md). It can optionally include attributes to verify the file's integrity: a file checksum and hashing algorithm as well as the file's size. Another optional field is a URL to download the image.
