import NautobotInput from "@shared/NautobotInput";
import NautobotSelect from "@shared/NautobotSelect";
import CreateViewTemplate from "@template/CreateViewTemplate";
import { duplicateInputValue } from "@utils/helpers";

const options = [
  { label: "No", value: "no" },
  { label: "Yes", value: "yes" },
];

export default function SiteAdd() {
  return (
    // <CreateViewTemplate pageTitle="Add a new site"/>
    // <CreateViewTemplate>
    //   <NautobotSelect
    //     label="Choose one option"
    //     options={options}
    //     hideIsValue="yes"
    //     hideInputId="name1"
    //   />
    //   <NautobotInput id="name1" _type="text" label="Name1" />
    //   <NautobotInput id="name2" _type="text" label="Name2" />
    //   <NautobotInput id="name3" _type="text" label="Name3" />
    // </CreateViewTemplate>
    <CreateViewTemplate pageTitle="Add a new site">
      <NautobotInput
        id="name1"
        _type="text"
        label="Name1"
        func={duplicateInputValue("name3", "name4")}
      />
      <NautobotInput id="name2" _type="text" label="Name2" />
      <NautobotInput id="name3" _type="text" label="Name3" />
      <NautobotInput id="name4" _type="text" label="Name4" />
    </CreateViewTemplate>
  );
}
