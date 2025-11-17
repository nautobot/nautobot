/**
 * Vue Router Routes Configuration
 *
 * Defines routes for the Vue 3 application, mapping to Django REST API endpoints
 */

import ControllerCreateView from './views/ControllerCreateView.vue';
import ControllerDetailView from './views/ControllerDetailView.vue';
import ControllerListView from './views/ControllerListView.vue';
import DeviceCreateView from './views/DeviceCreateView.vue';
import DeviceDetailView from './views/DeviceDetailView.vue';
import DeviceListView from './views/DeviceListView.vue';
import DeviceTypeCreateView from './views/DeviceTypeCreateView.vue';
import DeviceTypeDetailView from './views/DeviceTypeDetailView.vue';
import DeviceTypeListView from './views/DeviceTypeListView.vue';
import HomeView from './views/HomeView.vue';
import IPAddressCreateView from './views/IPAddressCreateView.vue';
import IPAddressDetailView from './views/IPAddressDetailView.vue';
import IPAddressListView from './views/IPAddressListView.vue';
import InterfaceCreateView from './views/InterfaceCreateView.vue';
import InterfaceDetailView from './views/InterfaceDetailView.vue';
import InterfaceListView from './views/InterfaceListView.vue';
import LocationCreateView from './views/LocationCreateView.vue';
import LocationDetailView from './views/LocationDetailView.vue';
import LocationListView from './views/LocationListView.vue';
import LocationTypeCreateView from './views/LocationTypeCreateView.vue';
import LocationTypeDetailView from './views/LocationTypeDetailView.vue';
import LocationTypeListView from './views/LocationTypeListView.vue';
import ManufacturerCreateView from './views/ManufacturerCreateView.vue';
import ManufacturerDetailView from './views/ManufacturerDetailView.vue';
import ManufacturerListView from './views/ManufacturerListView.vue';
import NamespaceCreateView from './views/NamespaceCreateView.vue';
import NamespaceDetailView from './views/NamespaceDetailView.vue';
import NamespaceListView from './views/NamespaceListView.vue';
import PlatformCreateView from './views/PlatformCreateView.vue';
import PlatformDetailView from './views/PlatformDetailView.vue';
import PlatformListView from './views/PlatformListView.vue';
import PrefixCreateView from './views/PrefixCreateView.vue';
import PrefixDetailView from './views/PrefixDetailView.vue';
import PrefixListView from './views/PrefixListView.vue';
import RackCreateView from './views/RackCreateView.vue';
import RackDetailView from './views/RackDetailView.vue';
import RackListView from './views/RackListView.vue';
import RoleCreateView from './views/RoleCreateView.vue';
import RoleDetailView from './views/RoleDetailView.vue';
import RoleListView from './views/RoleListView.vue';
import StatusCreateView from './views/StatusCreateView.vue';
import StatusDetailView from './views/StatusDetailView.vue';
import StatusListView from './views/StatusListView.vue';
// Generic views (use these for new models or migrate existing ones)
import GenericListView from './views/GenericListView.vue';
import GenericDetailView from './views/GenericDetailView.vue';
import GenericCreateView from './views/GenericCreateView.vue';
import VLANGroupCreateView from './views/VLANGroupCreateView.vue';
import VLANGroupDetailView from './views/VLANGroupDetailView.vue';
import VLANGroupListView from './views/VLANGroupListView.vue';
import VRFCreateView from './views/VRFCreateView.vue';
import VRFDetailView from './views/VRFDetailView.vue';
import VRFListView from './views/VRFListView.vue';

const routes = [
  {
    component: HomeView,
    name: 'home',
    path: '/',
  },
  {
    component: DeviceListView,
    name: 'device-list',
    path: '/devices',
  },
  {
    component: DeviceCreateView,
    name: 'device-create',
    path: '/devices/add',
  },
  {
    component: DeviceDetailView,
    name: 'device-detail',
    path: '/devices/:id',
    props: true,
  },
  {
    component: LocationListView,
    name: 'location-list',
    path: '/locations',
  },
  {
    component: LocationCreateView,
    name: 'location-create',
    path: '/locations/add',
  },
  {
    component: LocationDetailView,
    name: 'location-detail',
    path: '/locations/:id',
    props: true,
  },
  {
    component: PrefixListView,
    name: 'prefix-list',
    path: '/prefixes',
  },
  {
    component: PrefixCreateView,
    name: 'prefix-create',
    path: '/prefixes/add',
  },
  {
    component: PrefixDetailView,
    name: 'prefix-detail',
    path: '/prefixes/:id',
    props: true,
  },
  {
    component: RackListView,
    name: 'rack-list',
    path: '/racks',
  },
  {
    component: RackCreateView,
    name: 'rack-create',
    path: '/racks/add',
  },
  {
    component: RackDetailView,
    name: 'rack-detail',
    path: '/racks/:id',
    props: true,
  },
  {
    component: ManufacturerListView,
    name: 'manufacturer-list',
    path: '/manufacturers',
  },
  {
    component: ManufacturerCreateView,
    name: 'manufacturer-create',
    path: '/manufacturers/add',
  },
  {
    component: ManufacturerDetailView,
    name: 'manufacturer-detail',
    path: '/manufacturers/:id',
    props: true,
  },
  {
    component: DeviceTypeListView,
    name: 'device-type-list',
    path: '/device-types',
  },
  {
    component: DeviceTypeCreateView,
    name: 'device-type-create',
    path: '/device-types/add',
  },
  {
    component: DeviceTypeDetailView,
    name: 'device-type-detail',
    path: '/device-types/:id',
    props: true,
  },
  {
    component: InterfaceListView,
    name: 'interface-list',
    path: '/interfaces',
  },
  {
    component: InterfaceCreateView,
    name: 'interface-create',
    path: '/interfaces/add',
  },
  {
    component: InterfaceDetailView,
    name: 'interface-detail',
    path: '/interfaces/:id',
    props: true,
  },
  {
    component: LocationTypeListView,
    name: 'location-type-list',
    path: '/location-types',
  },
  {
    component: LocationTypeCreateView,
    name: 'location-type-create',
    path: '/location-types/add',
  },
  {
    component: LocationTypeDetailView,
    name: 'location-type-detail',
    path: '/location-types/:id',
    props: true,
  },
  // Using generic views (can replace RoleListView, RoleCreateView, RoleDetailView)
  {
    component: GenericListView,
    name: 'role-list',
    path: '/roles',
  },
  {
    component: GenericCreateView,
    name: 'role-create',
    path: '/roles/add',
  },
  {
    component: GenericDetailView,
    name: 'role-detail',
    path: '/roles/:id',
    props: true,
  },
  // Legacy specific views (can be removed after migration)
  // {
  //   component: RoleListView,
  //   name: 'role-list',
  //   path: '/roles',
  // },
  // {
  //   component: RoleCreateView,
  //   name: 'role-create',
  //   path: '/roles/add',
  // },
  // {
  //   component: RoleDetailView,
  //   name: 'role-detail',
  //   path: '/roles/:id',
  //   props: true,
  // },
  {
    component: PlatformListView,
    name: 'platform-list',
    path: '/platforms',
  },
  {
    component: PlatformCreateView,
    name: 'platform-create',
    path: '/platforms/add',
  },
  {
    component: PlatformDetailView,
    name: 'platform-detail',
    path: '/platforms/:id',
    props: true,
  },
  // Using generic views (can replace StatusListView, StatusCreateView, StatusDetailView)
  {
    component: GenericListView,
    name: 'status-list',
    path: '/statuses',
  },
  {
    component: GenericCreateView,
    name: 'status-create',
    path: '/statuses/add',
  },
  {
    component: GenericDetailView,
    name: 'status-detail',
    path: '/statuses/:id',
    props: true,
  },
  // Legacy specific views (can be removed after migration)
  // {
  //   component: StatusListView,
  //   name: 'status-list',
  //   path: '/statuses',
  // },
  // {
  //   component: StatusCreateView,
  //   name: 'status-create',
  //   path: '/statuses/add',
  // },
  // {
  //   component: StatusDetailView,
  //   name: 'status-detail',
  //   path: '/statuses/:id',
  //   props: true,
  // },
  {
    component: NamespaceListView,
    name: 'namespace-list',
    path: '/namespaces',
  },
  {
    component: NamespaceCreateView,
    name: 'namespace-create',
    path: '/namespaces/add',
  },
  {
    component: NamespaceDetailView,
    name: 'namespace-detail',
    path: '/namespaces/:id',
    props: true,
  },
  {
    component: IPAddressListView,
    name: 'ip-address-list',
    path: '/ip-addresses',
  },
  {
    component: IPAddressCreateView,
    name: 'ip-address-create',
    path: '/ip-addresses/add',
  },
  {
    component: IPAddressDetailView,
    name: 'ip-address-detail',
    path: '/ip-addresses/:id',
    props: true,
  },
  {
    component: VRFListView,
    name: 'vrf-list',
    path: '/vrfs',
  },
  {
    component: VRFCreateView,
    name: 'vrf-create',
    path: '/vrfs/add',
  },
  {
    component: VRFDetailView,
    name: 'vrf-detail',
    path: '/vrfs/:id',
    props: true,
  },
  {
    component: VLANGroupListView,
    name: 'vlan-group-list',
    path: '/vlan-groups',
  },
  {
    component: VLANGroupCreateView,
    name: 'vlan-group-create',
    path: '/vlan-groups/add',
  },
  {
    component: VLANGroupDetailView,
    name: 'vlan-group-detail',
    path: '/vlan-groups/:id',
    props: true,
  },
  {
    component: ControllerListView,
    name: 'controller-list',
    path: '/controllers',
  },
  {
    component: ControllerCreateView,
    name: 'controller-create',
    path: '/controllers/add',
  },
  {
    component: ControllerDetailView,
    name: 'controller-detail',
    path: '/controllers/:id',
    props: true,
  },
];

export default routes;
