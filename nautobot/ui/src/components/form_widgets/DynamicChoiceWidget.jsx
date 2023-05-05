import BaseFormWidget from "./BaseFormWidget";
import { ariaDescribedByIds } from '@rjsf/utils';
import { useGetRESTAPIQuery } from "@utils/api";
import AsyncSelect from 'react-select/async';
// FixMe: Cant use this because of incompatible styling with current form; Using `AsyncSelect` for now
// import { ReactSelectAsync } from "@nautobot/nautobot-ui";
import { getContrastColor } from "@utils/color";



const colourStyles = {
    control: (styles) => ({ ...styles }),
    option: (styles, { data, isDisabled, isFocused, isSelected }) => ({...styles, color:"#000"}),
    multiValue: (styles, { data }) => ({...styles, color: getContrastColor(data.color)}),
    multiValueLabel: (styles, { data }) => ({...styles, color: getContrastColor(data.color), backgroundColor: data.color}),
    multiValueRemove: (styles, { data }) => ({...styles, color: getContrastColor(data.color), backgroundColor: data.color}),
};


export default function DynamicChoiceWidget({ isMulti, ...props}) {
    const {id, value, autofocus, schema, onBlur, onFocus, onChange, options } = props
    // const _onChange = (props) => {
    //     console.log("=== ", props)
    // }
    // onChange(value === '' ? options.emptyValue : value);
    // const _onBlur = ({ target: { value } }) => onBlur(id, value);
    // const _onFocus = ({ target: { value } }) => onFocus(id, value);

    const {app_label, model_name} = schema.additionalProps;
    let searchQuery = {app_name: app_label, model_name, depth: 0};
    let extra_props = {}
    const { data: listData } = useGetRESTAPIQuery(searchQuery);
    
    const loadOptions = (inputValue, callback) => {
        if (listData) {
            const data = listData.results.map(item => { return {
                value: item.id,
                label: item.display,
                color: item.color ? "#" + item.color : "",
                backgroundColor: item.color ? "#" + item.color : "",
            }})
            callback(data);
        }
    };
    if (isMulti) {
        extra_props.isMulti = true;
    }

  return (
    <BaseFormWidget {...props} >
        <AsyncSelect 
            id={id}
            name={id} 
            // value={value ?? ""} 
            cacheOptions 
            loadOptions={loadOptions} 
            defaultOptions {...extra_props} 
            styles={colourStyles} 
            autoFocus={autofocus}
            // onChange={_onChange}
            // onBlur={_onBlur}
            // onFocus={_onFocus}
            aria-describedby={ariaDescribedByIds(id)}
        />
    </BaseFormWidget>
  );
}