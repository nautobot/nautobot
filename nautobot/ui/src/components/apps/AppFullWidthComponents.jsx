
import AppComponents from "@components/core/Apps"


export default function AppFullWidthComponentsWithProps(route, props) {
    if (!AppComponents.FullWidthComponents?.[route]) return <></>
    return AppComponents['FullWidthComponents'][route].map((FullWidthComponent, idx) =>
        <FullWidthComponent {...props} key={idx} />
    );
}
