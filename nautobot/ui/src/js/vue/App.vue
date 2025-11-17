<template>
    <div id="nautobot-vue-app" class="nautobot-vue-app">
        <nav
            class="navbar navbar-expand-lg navbar-dark bg-dark mb-4"
            v-if="showNavbar"
        >
            <div class="container-fluid">
                <router-link class="navbar-brand" to="/">
                    <i class="mdi mdi-nautobot"></i> Nautobot Vue
                </router-link>
                <button
                    class="navbar-toggler"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#navbarNav"
                >
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav me-auto">
                        <li class="nav-item dropdown">
                            <a
                                class="nav-link dropdown-toggle"
                                href="#"
                                role="button"
                                data-bs-toggle="dropdown"
                                aria-expanded="false"
                            >
                                DCIM
                            </a>
                            <ul class="dropdown-menu">
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/devices"
                                        >Devices</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/device-types"
                                        >Device Types</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/manufacturers"
                                        >Manufacturers</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/interfaces"
                                        >Interfaces</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/locations"
                                        >Locations</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/location-types"
                                        >Location Types</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/racks"
                                        >Racks</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/platforms"
                                        >Platforms</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/controllers"
                                        >Controllers</router-link
                                    >
                                </li>
                            </ul>
                        </li>
                        <li class="nav-item dropdown">
                            <a
                                class="nav-link dropdown-toggle"
                                href="#"
                                role="button"
                                data-bs-toggle="dropdown"
                                aria-expanded="false"
                            >
                                IPAM
                            </a>
                            <ul class="dropdown-menu">
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/prefixes"
                                        >Prefixes</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/ip-addresses"
                                        >IP Addresses</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/vrfs"
                                        >VRFs</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/vlan-groups"
                                        >VLAN Groups</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/namespaces"
                                        >Namespaces</router-link
                                    >
                                </li>
                            </ul>
                        </li>
                        <li class="nav-item dropdown">
                            <a
                                class="nav-link dropdown-toggle"
                                href="#"
                                role="button"
                                data-bs-toggle="dropdown"
                                aria-expanded="false"
                            >
                                Extras
                            </a>
                            <ul class="dropdown-menu">
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/statuses"
                                        >Statuses</router-link
                                    >
                                </li>
                                <li>
                                    <router-link
                                        class="dropdown-item"
                                        to="/roles"
                                        >Roles</router-link
                                    >
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            </div>
        </nav>

        <div class="container-fluid h-100">
            <router-view v-slot="{ Component }">
                <transition name="fade" mode="out-in">
                    <component :is="Component" />
                </transition>
            </router-view>
        </div>
    </div>
</template>

<script>
export default {
    name: 'App',
    data() {
        return {
            showNavbar: true, // Can be controlled via props or config
        };
    },
    mounted() {
        // Check if we're embedded in a Django template (navbar might be handled by Django)
        if (document.querySelector('.nautobot-navbar')) {
            this.showNavbar = false;
        }
    },
};
</script>

<style scoped>
.nautobot-vue-app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.nautobot-vue-app .container-fluid {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
