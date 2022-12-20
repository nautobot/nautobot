import Badge from 'react-bootstrap/Badge';
import { Link } from "react-router-dom";

export default function BSTableItem({ name, obj, url, link = false }) {
  let display = ""
  if (obj == null) {
    display = "—"
  } else if (Array.isArray(obj)) {
    display = JSON.stringify(obj)
    if (typeof obj[0] == "object") {
      display = obj.map((item, idx) => (
        <span className="badge" key={idx} style={{ backgroundColor: "#" + item.color }}>
          {item.display || item.label}
        </span>
      ))
    } else {
      display = obj.join(", ")
    }
  } else if (typeof obj == "object") {
    display = obj.display || obj.label
  } else {
    if (obj === "") {
      display = "—"
    } else {
      display = obj
    }
  }
  return (
    <>
      {/* {JSON.stringify(obj)} */}
      {/* {
        !href
          ? <>null</>
          : <>{href}</>
      } */}
      {!!link
        ? <Link to={url}>{display}</Link>
        : display
      }
    </>
    // item[header.name] == null
    //     ? "-"
    //     : Array.isArray(item[header.name])
    //         ? item[header.name].join(", ")
    //         : typeof item[header.name] == "object"
    //             ? item[header.name].label || item[header.name].display
    //             : idx === 0
    //                 ? <Link href={window.location.pathname + "/" + item["id"]}>{item[header.name]}</Link>
    //                 : item[header.name]
  )
}
