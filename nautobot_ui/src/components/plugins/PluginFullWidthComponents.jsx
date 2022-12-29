
import PluginComponents from "@components/core/Plugins"


export default function PluginFullWidthComponentsWithProps(route, props) {
    if (!PluginComponents.FullWidthComponents?.[route]) return <></>
    return PluginComponents['FullWidthComponents'][route].map((FullWidthComponent, idx) =>
        <FullWidthComponent {...props} key={idx} />
    );
}
