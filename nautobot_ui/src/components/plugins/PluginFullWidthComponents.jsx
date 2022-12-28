
import PluginComponents from "@components/core/Plugins"


const PluginFullWidthComponents = PluginComponents['FullWidthComponents'].map((FullWidthComponent) =>
    <FullWidthComponent />
);

export function PluginFullWidthComponentsWithProps(props) {
    return PluginComponents['FullWidthComponents'].map((FullWidthComponent, idx) =>
        <FullWidthComponent {...props} key={idx} />
    );
}
export default PluginFullWidthComponents;
