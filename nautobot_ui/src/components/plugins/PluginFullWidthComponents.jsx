
import PluginComponents from "@components/core/Plugins"


export default function PluginFullWidthComponentsWithProps(route, props) {
    console.log(PluginComponents.FullWidthComponents)
    console.log(`My route is ${route}`)
    if (!PluginComponents.FullWidthComponents?.[route]) return <></>
    return PluginComponents['FullWidthComponents'][route].map((FullWidthComponent, idx) =>
        <FullWidthComponent {...props} key={idx} />
    );
}
