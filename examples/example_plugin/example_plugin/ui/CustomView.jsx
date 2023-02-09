// TODO: this should be moved to example_plugin_with_view_override, as it is being used to replace the default view for
// IPAddress objects, which is not something example_plugin should be doing.
import Table from 'react-bootstrap/Table';

export function CustomTableView(props) {
  return (
    <Table striped bordered hover>
      <thead>
        <tr>
          <th>Key</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>ID</td>
          <td>{props.id}</td>
        </tr>
        <tr>
          <td>Display</td>
          <td>{props.display}</td>
        </tr>
        <tr>
          <td>Web URL</td>
          <td>{props.web_url}</td>
        </tr>
      </tbody>
    </Table>
  );
}

export default CustomTableView;
