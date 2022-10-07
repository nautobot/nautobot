# Image Attachments

Certain objects in Nautobot support the attachment of uploaded images. These will be saved to the Nautobot server and made available whenever the object is viewed.

The location of where image attachments are stored can be customized using the [`MEDIA_ROOT`](../../configuration/optional-settings.md#media_root) setting in your `nautobot_config.py`.

Currently, the following types of image attachments can be stored in Nautobot:

- Device type images are stored at `$MEDIA_ROOT/devicetype-images`
- Generic image attachments are stored at `$MEDIA_ROOT/image-attachments`
