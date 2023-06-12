import svgwrite

from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode

from .choices import DeviceFaceChoices
from .constants import RACK_ELEVATION_BORDER_WIDTH


class RackElevationSVG:
    """
    Use this class to render a rack elevation as an SVG image.

    :param rack: A Nautobot Rack instance
    :param user: User instance. If specified, only devices viewable by this user will be fully displayed.
    :param include_images: If true, the SVG document will embed front/rear device face images, where available
    :param base_url: Base URL for links within the SVG document. If none, links will be relative.
    """

    def __init__(self, rack, user=None, include_images=True, base_url=None, display_fullname=True):
        self.rack = rack
        self.include_images = include_images
        self.display_fullname = display_fullname
        if base_url is not None:
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = ""

        # Determine the subset of devices within this rack that are viewable by the user, if any
        permitted_devices = self.rack.devices
        if user is not None:
            permitted_devices = permitted_devices.restrict(user, "view")
        self.permitted_device_ids = permitted_devices.values_list("pk", flat=True)

    @staticmethod
    def _get_device_description(device):
        return "{} ({}) — {} ({}U) {} {}".format(  # pylint: disable=consider-using-f-string
            device.name,
            device.role,
            device.device_type.display,
            device.device_type.u_height,
            device.asset_tag or "",
            device.serial or "",
        )

    @staticmethod
    def _add_gradient(drawing, id_, color, angle=45):
        gradient = drawing.linearGradient(
            start=(0, 0),
            end=(0, 25),
            spreadMethod="repeat",
            id_=id_,
            gradientTransform=f"rotate({angle}, 0, 0)",
            gradientUnits="userSpaceOnUse",
        )
        gradient.add_stop_color(offset="0%", color="#f7f7f7")
        gradient.add_stop_color(offset="50%", color="#f7f7f7")
        gradient.add_stop_color(offset="50%", color=color)
        gradient.add_stop_color(offset="100%", color=color)
        drawing.defs.add(gradient)

    @staticmethod
    def _add_filters(drawing):
        new_filter = drawing.filter(id="darkmodeinvert")
        fct = new_filter.feComponentTransfer(color_interpolation_filters="sRGB", result="inverted")
        fct.feFuncR("table", tableValues="1,0")
        fct.feFuncG("table", tableValues="1,0")
        fct.feFuncB("table", tableValues="1,0")
        new_filter.feColorMatrix(type_="hueRotate", values="180", in_="inverted")
        drawing.defs.add(new_filter)

    @staticmethod
    def _setup_drawing(width, height):
        drawing = svgwrite.Drawing(size=(width, height))

        # add the stylesheet
        with open(f"{settings.STATICFILES_DIRS[0]}/css/rack_elevation.css") as css_file:
            drawing.defs.add(drawing.style(css_file.read()))

        # add gradients
        RackElevationSVG._add_gradient(drawing, "reserved", "#c7c7ff")
        RackElevationSVG._add_gradient(drawing, "occupied", "#d7d7d7")
        RackElevationSVG._add_gradient(drawing, "blocked", "#ffc0c0")
        RackElevationSVG._add_gradient(drawing, "blocked_partial", "#a0a0a0", angle=-45)
        RackElevationSVG._add_filters(drawing)

        return drawing

    def _draw_device_front(self, drawing, device, start, end, text):
        device_bay_details = ""
        if device.device_bay_count:
            device_bay_details += f" ({device.get_children().count()}/{device.device_bay_count})"

        device_fullname = str(device) + device_bay_details
        device_shortname = settings.UI_RACK_VIEW_TRUNCATE_FUNCTION(str(device)) + device_bay_details

        color = device.role.color
        reverse_url = reverse("dcim:device", kwargs={"pk": device.pk})
        link = drawing.add(
            drawing.a(
                href=f"{self.base_url}{reverse_url}",
                target="_top",
                fill="black",
            )
        )
        link.set_desc(self._get_device_description(device))
        link.add(drawing.rect(start, end, style=f"fill: #{color}", class_="slot"))

        # Embed front device type image if one exists
        if self.include_images and device.device_type.front_image:
            image = drawing.image(
                href=device.device_type.front_image.url,
                insert=start,
                size=end,
                class_="device-image",
            )
            image.fit(scale="slice")
            link.add(image)

        link.add(
            drawing.text(
                device_fullname,
                insert=text,
                fill="white",
                style="text-shadow: 1px 1px 3px black;",
                class_=f"rack-device-fullname{'' if self.display_fullname else ' hidden'}",
            )
        )
        link.add(
            drawing.text(
                device_shortname,
                insert=text,
                fill="white",
                style="text-shadow: 1px 1px 3px black;",
                class_=f"rack-device-shortname{' hidden' if self.display_fullname else ''}",
            )
        )

    def _draw_device_rear(self, drawing, device, start, end, text):
        rect = drawing.rect(start, end, class_="slot blocked")
        rect.set_desc(self._get_device_description(device))

        device_fullname = str(device)
        device_shortname = settings.UI_RACK_VIEW_TRUNCATE_FUNCTION(str(device))

        drawing.add(rect)

        # Embed rear device type image if one exists
        if self.include_images and device.device_type.rear_image:
            image = drawing.image(
                href=device.device_type.rear_image.url,
                insert=start,
                size=end,
                class_="device-image",
            )
            image.fit(scale="slice")
            drawing.add(image)

        drawing.add(
            drawing.text(
                device_fullname,
                insert=text,
                fill="white",
                style="text-shadow: 1px 1px 3px black;",
                class_=f"rack-device-fullname{'' if self.display_fullname else ' hidden'}",
            )
        )
        drawing.add(
            drawing.text(
                device_shortname,
                insert=text,
                fill="white",
                style="text-shadow: 1px 1px 3px black;",
                class_=f"rack-device-shortname{' hidden' if self.display_fullname else ''}",
            )
        )

    @staticmethod
    def _draw_empty(drawing, rack, start, end, text, id_, face_id, class_, reservation):
        reverse_url = reverse("dcim:device_add")
        query_params = urlencode(
            {
                "rack": rack.pk,
                "location": rack.location.pk,
                "face": face_id,
                "position": id_,
            }
        )
        link = drawing.add(
            drawing.a(
                href=f"{reverse_url}?{query_params}",
                target="_top",
            )
        )
        if reservation:
            link.set_desc(f"{reservation.description} — {reservation.user} · {reservation.created}")
        link.add(drawing.rect(start, end, class_=class_))
        link.add(drawing.text("add device", insert=text, class_="add-device"))

    def merge_elevations(self, face):
        elevation = self.rack.get_rack_units(face=face, expand_devices=False)
        if face == DeviceFaceChoices.FACE_REAR:
            other_face = DeviceFaceChoices.FACE_FRONT
        else:
            other_face = DeviceFaceChoices.FACE_REAR
        other = self.rack.get_rack_units(face=other_face)

        unit_cursor = 0
        for u in elevation:
            o = other[unit_cursor]
            if not u["device"] and o["device"]:
                u["device"] = o["device"]
                u["height"] = 1
            unit_cursor += u.get("height", 1)

        return elevation

    def render(self, face, unit_width, unit_height, legend_width):
        """
        Return an SVG document representing a rack elevation.
        """
        drawing = self._setup_drawing(
            unit_width + legend_width + RACK_ELEVATION_BORDER_WIDTH * 2,
            unit_height * self.rack.u_height + RACK_ELEVATION_BORDER_WIDTH * 2,
        )
        reserved_units = self.rack.get_reserved_units()

        unit_cursor = 0
        for ru in range(0, self.rack.u_height):
            start_y = ru * unit_height
            position_coordinates = (
                legend_width / 2,
                start_y + unit_height / 2 + RACK_ELEVATION_BORDER_WIDTH,
            )
            unit = ru + 1 if self.rack.desc_units else self.rack.u_height - ru
            drawing.add(drawing.text(str(unit), position_coordinates, class_="unit"))

        for unit in self.merge_elevations(face):
            # Loop through all units in the elevation
            device = unit["device"]
            height = unit.get("height", 1)

            # Setup drawing coordinates
            x_offset = legend_width + RACK_ELEVATION_BORDER_WIDTH
            y_offset = unit_cursor * unit_height + RACK_ELEVATION_BORDER_WIDTH
            end_y = unit_height * height
            start_coordinates = (x_offset, y_offset)
            end_coordinates = (unit_width, end_y)
            text_coordinates = (x_offset + (unit_width / 2), y_offset + end_y / 2)

            # Draw the device
            if device and device.pk in self.permitted_device_ids:
                if device.face == face:
                    self._draw_device_front(drawing, device, start_coordinates, end_coordinates, text_coordinates)
                elif device.device_type.is_full_depth:
                    self._draw_device_rear(drawing, device, start_coordinates, end_coordinates, text_coordinates)
                else:
                    # Half-depth devices add an empty box that is partially blocked
                    self._draw_empty(
                        drawing,
                        self.rack,
                        start_coordinates,
                        end_coordinates,
                        text_coordinates,
                        unit["id"],
                        face,
                        "slot blocked_partial",
                        None,
                    )
            elif device:
                # Devices which the user does not have permission to view are rendered only as unavailable space
                drawing.add(drawing.rect(start_coordinates, end_coordinates, class_="blocked"))
            else:
                # Draw shallow devices, reservations, or empty units
                class_ = "slot"
                reservation = reserved_units.get(unit["id"])
                if device:
                    class_ += " occupied"
                if reservation:
                    class_ += " reserved"
                self._draw_empty(
                    drawing,
                    self.rack,
                    start_coordinates,
                    end_coordinates,
                    text_coordinates,
                    unit["id"],
                    face,
                    class_,
                    reservation,
                )

            unit_cursor += height

        # Wrap the drawing with a border
        border_width = RACK_ELEVATION_BORDER_WIDTH
        border_offset = RACK_ELEVATION_BORDER_WIDTH / 2
        frame = drawing.rect(
            insert=(legend_width + border_offset, border_offset),
            size=(
                unit_width + border_width,
                self.rack.u_height * unit_height + border_width,
            ),
            class_="rack",
        )
        drawing.add(frame)

        return drawing
