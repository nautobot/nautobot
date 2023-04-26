import AppComponents from "@components/Apps";

export default function AppFullWidthComponentsWithProps(route, props) {
    if (!AppComponents.FullWidthComponents?.[route]) return <></>;
    return AppComponents["FullWidthComponents"][route].map(
        (FullWidthComponent, idx) => <FullWidthComponent {...props} key={idx} />
    );
}
