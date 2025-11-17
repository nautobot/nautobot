<template>
    <div class="home-view">
        <div class="row">
            <div class="col-12">
                <h1 class="mb-4">Nautobot Vue 3 Frontend</h1>
                <p class="lead">Welcome to the Vue 3 frontend for Nautobot.</p>

                <h2 class="mt-5 mb-3">DCIM</h2>
                <div class="row">
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-server"></i> Devices
                                </h5>
                                <p class="card-text">
                                    Browse and manage network devices.
                                </p>
                                <router-link
                                    to="/devices"
                                    class="btn btn-primary"
                                    >View Devices</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-chip"></i> Device Types
                                </h5>
                                <p class="card-text">
                                    Manage device models and manufacturers.
                                </p>
                                <router-link
                                    to="/device-types"
                                    class="btn btn-primary"
                                    >View Device Types</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-factory"></i>
                                    Manufacturers
                                </h5>
                                <p class="card-text">
                                    Manage device manufacturers.
                                </p>
                                <router-link
                                    to="/manufacturers"
                                    class="btn btn-primary"
                                    >View Manufacturers</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-ethernet-cable"></i>
                                    Interfaces
                                </h5>
                                <p class="card-text">
                                    Manage device network interfaces.
                                </p>
                                <router-link
                                    to="/interfaces"
                                    class="btn btn-primary"
                                    >View Interfaces</router-link
                                >
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row mt-3">
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-map-marker"></i> Locations
                                </h5>
                                <p class="card-text">
                                    Manage physical locations and sites.
                                </p>
                                <router-link
                                    to="/locations"
                                    class="btn btn-primary"
                                    >View Locations</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-server-rack"></i> Racks
                                </h5>
                                <p class="card-text">
                                    Manage equipment racks and rack groups.
                                </p>
                                <router-link to="/racks" class="btn btn-primary"
                                    >View Racks</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-folder-multiple"></i>
                                    Location Types
                                </h5>
                                <p class="card-text">
                                    Manage location type definitions.
                                </p>
                                <router-link
                                    to="/location-types"
                                    class="btn btn-primary"
                                    >View Location Types</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-laptop"></i> Platforms
                                </h5>
                                <p class="card-text">
                                    Manage device platforms and operating
                                    systems.
                                </p>
                                <router-link
                                    to="/platforms"
                                    class="btn btn-primary"
                                    >View Platforms</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-controller"></i>
                                    Controllers
                                </h5>
                                <p class="card-text">
                                    Manage network controllers and management
                                    systems.
                                </p>
                                <router-link
                                    to="/controllers"
                                    class="btn btn-primary"
                                    >View Controllers</router-link
                                >
                            </div>
                        </div>
                    </div>
                </div>

                <h2 class="mt-5 mb-3">IPAM</h2>
                <div class="row">
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-ip-network"></i> Prefixes
                                </h5>
                                <p class="card-text">
                                    Manage IP address prefixes and subnets.
                                </p>
                                <router-link
                                    to="/prefixes"
                                    class="btn btn-primary"
                                    >View Prefixes</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-ip"></i> IP Addresses
                                </h5>
                                <p class="card-text">
                                    Manage individual IP addresses and
                                    assignments.
                                </p>
                                <router-link
                                    to="/ip-addresses"
                                    class="btn btn-primary"
                                    >View IP Addresses</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-router-network"></i> VRFs
                                </h5>
                                <p class="card-text">
                                    Manage Virtual Routing and Forwarding
                                    tables.
                                </p>
                                <router-link to="/vrfs" class="btn btn-primary"
                                    >View VRFs</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-network"></i> VLAN Groups
                                </h5>
                                <p class="card-text">
                                    Manage VLAN groups and VLAN assignments.
                                </p>
                                <router-link
                                    to="/vlan-groups"
                                    class="btn btn-primary"
                                    >View VLAN Groups</router-link
                                >
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row mt-3">
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-folder-network"></i>
                                    Namespaces
                                </h5>
                                <p class="card-text">
                                    Manage IP address namespaces for network
                                    isolation.
                                </p>
                                <router-link
                                    to="/namespaces"
                                    class="btn btn-primary"
                                    >View Namespaces</router-link
                                >
                            </div>
                        </div>
                    </div>
                </div>

                <h2 class="mt-5 mb-3">Extras</h2>
                <div class="row">
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-check-circle"></i>
                                    Statuses
                                </h5>
                                <p class="card-text">
                                    Manage status definitions for various
                                    objects.
                                </p>
                                <router-link
                                    to="/statuses"
                                    class="btn btn-primary"
                                    >View Statuses</router-link
                                >
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="mdi mdi-tag"></i> Roles
                                </h5>
                                <p class="card-text">
                                    Manage role definitions for devices and
                                    other objects.
                                </p>
                                <router-link to="/roles" class="btn btn-primary"
                                    >View Roles</router-link
                                >
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'HomeView',
};
</script>

<style scoped>
.home-view {
    padding: 2rem 0;
}

.card {
    height: 100%;
    transition: transform 0.2s;
}

.card:hover {
    transform: translateY(-5px);
}
</style>
