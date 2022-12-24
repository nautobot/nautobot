export function MarketPlaceCard({name}) {
    return (
        <div className="border-2 rounded-lg" style={{ width: "32.45%" }}>
            <div className="border-b-2 p-4">
                <h3 className="text-2xl font-bold">{name}</h3>
                Nautobot core team
            </div>
            <div className="border-b-2 p-4 text-gray-400">
                Lorem ipsum dolor sit amet consectetur, adipisicing elit.
                Assumenda consequatur doloremque iste at accusamus eum officiis laborum quo eligendi...
            </div>
            <div className="px-2 p-4 flex justify-between">
                <span className="text-gray-400">22 214 downloads</span>

                <button className="bg-blue-500 text-white py-1 px-5 rounded-lg"> Get</button>
            </div>
        </div>
    )
}