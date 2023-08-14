import NautobotApps from "@generated/app_imports";

function EmptyElement() {
    return <></>;
}

function findOrEmpty(module, key) {
    return key in module ? module[key] : EmptyElement;
}

export function getComponentFromModule(module_name, component_name) {
    return NautobotApps[module_name]
        .then((module) => ({ default: findOrEmpty(module, component_name) }))
        .catch({ default: EmptyElement });
}
