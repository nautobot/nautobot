import DynamicChoiceWidget from "./DynamicChoiceWidget";

export default function DynamicMultiChoiceWidget(props) {
  return (
    <DynamicChoiceWidget isMulti={true} {...props} />
  );
}