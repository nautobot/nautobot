import { Table } from '@nautobot/nautobot-ui';

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
          <td>URL</td>
          <td>{props.url}</td>
        </tr>
      </tbody>
    </Table>
  );
}

export default CustomTableView;
