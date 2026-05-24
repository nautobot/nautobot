"""Tests for ModuleType per-object component add routes (issue #8741)"""
import pytest
from django.urls import reverse, resolve
from django.test import Client


@pytest.mark.django_db
class TestModuleTypeComponentAddRoutes:
    """Test that ModuleType per-object component add routes work correctly."""

    # 8 个组件类型及其对应的 URL name
    COMPONENT_ROUTES = [
        ("moduletype_consoleporttemplate_add", "console-ports"),
        ("moduletype_consoleserverporttemplate_add", "console-server-ports"),
        ("moduletype_powerporttemplate_add", "power-ports"),
        ("moduletype_poweroutlettemplate_add", "power-outlets"),
        ("moduletype_interfacetemplate_add", "interfaces"),
        ("moduletype_frontporttemplate_add", "front-ports"),
        ("moduletype_rearporttemplate_add", "rear-ports"),
        ("moduletype_modulebaytemplate_add", "module-bays"),
    ]

    @pytest.fixture
    def module_type(self, db):
        """创建一个 ModuleType 用于测试"""
        from nautobot.dcim.models import ModuleType, Manufacturer
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer")
        return ModuleType.objects.create(
            manufacturer=manufacturer,
            model="Test Module Type",
        )

    @pytest.mark.parametrize("url_name,expected_tab", COMPONENT_ROUTES)
    def test_route_resolves(self, url_name, expected_tab, module_type):
        """测试 URL 路由能正确解析"""
        url = reverse(f"dcim:{url_name}", kwargs={"pk": module_type.pk})
        assert f"/dcim/module-types/{module_type.pk}/" in url
        # 验证 URL 能被正确解析回 view
        resolved = resolve(url)
        assert resolved.url_name == url_name

    @pytest.mark.parametrize("url_name,expected_tab", COMPONENT_ROUTES)
    def test_route_redirects(self, url_name, expected_tab, module_type, client):
        """测试 RedirectView 正确重定向到创建页面"""
        url = reverse(f"dcim:{url_name}", kwargs={"pk": module_type.pk})
        response = client.get(url)
        assert response.status_code == 302
        location = response.url
        assert "module_type=" in location
        assert str(module_type.pk) in location
        assert "return_url=" in location

    def test_device_type_routes_still_work(self, db):
        """确保 DeviceType 的路由没有被影响"""
        from nautobot.dcim.models import DeviceType, Manufacturer
        manufacturer = Manufacturer.objects.create(name="Test Mfr 2")
        dt = DeviceType.objects.create(manufacturer=manufacturer, model="Test DT")

        url = reverse("dcim:devicetype_consoleporttemplate_add", kwargs={"pk": dt.pk})
        assert f"/dcim/device-types/{dt.pk}/console-port-templates/add/" == url
