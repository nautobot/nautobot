import Link from "next/link"

export default function Linked({ obj }) {
  return (
    <>
      {
        obj.url
          ? <Link href={obj.url}>{obj}</Link>
          : obj
      }
    </>
  )
}
