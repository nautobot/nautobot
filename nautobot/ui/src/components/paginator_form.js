import React from "react";
import { Box, Text, Select } from "@nautobot/nautobot-ui";
// import { useSearchParams } from "react-router-dom";

// export default function PaginatorForm({ start, end, total_count }) {
//     // let [searchParams, setSearchParams] = useSearchParams();
//     let paginator_string = `Showing ${start} - ${end} of ${total_count}`;
//     // const { setType } = useState("PaginatorForm");

//     return (
//         <Box width="200px">
//             <Select onChange={this.onPageSizeChange.bind(this)}>
//                 <option>50</option>
//                 <option>100</option>
//                 <option>200</option>
//                 <option>500</option>
//             </Select>
//             <Text>{paginator_string}</Text>
//         </Box>
//         // TODO: come up with equivalent nautobot-ui pattern to the below, from react-bootstrap
//         /*
//     <Col sm={3}>
//       <Form.Control
//         as="select"
//         // Default value
//         value={searchParams.get("limit") || 50}
//         onChange={e => {
//           // Set the input value
//           setType(e.target.value);
//           // Change the query parameters on form change
//           setSearchParams({ limit: e.target.value, offset: 0 })
//         }}
//       >
//         <option>50</option>
//         <option>100</option>
//         <option>200</option>
//         <option>500</option>
//       </Form.Control>
//       <Form.Text muted>
//         {paginator_string}
//       </Form.Text>
//     </Col >
//     */
//     );
// }

class PaginatorForm extends React.Component {
  constructor(props){
    super(props);
    this.state = {};
  }
  
  onPageSizeChange(event) {
    // parent class change handler is always called with field name and value
    this.props.onChange("page_size", event.target.value);
  } 

  render () {
    let paginator_string = `Showing ${this.props.start} - ${this.props.end} of ${this.props.total_count}`;
    return (
        <Box width="300px">
            <Select onChange={this.onPageSizeChange.bind(this)}>
                <option>50</option>
                <option>100</option>
                <option>200</option>
                <option>500</option>
            </Select>
            <Text>{paginator_string}</Text>
        </Box>
    )
  }
}
export default PaginatorForm;