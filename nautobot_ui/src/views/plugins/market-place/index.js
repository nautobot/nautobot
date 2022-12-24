import { BaseLayout, MarketPlaceCard } from "@nautobot/components";

const bannerStyle = {
    backgroundImage: `url(/assets/images/bg.jpg)`,
    backgroundSize: "cover",
    height: "40vh",
}

const plugins = [
    {
        name: "Example Plugin",
    },
    {
        name: "Golden Config",
    },
    {
        name: "ChartJS Magnify",
    },
    {
        name: "Sample Text Plugin",
    },
    {
        name: "Full Model Simplify",
    },
    {
        name: "Code With Me Plugin",
    }
]


export default function MarketPlace() {
    return (
        <main className="relative min-h-screen bg-white">
            <div className="flex h-full min-h-screen flex-col">
                <main className="h-full bg-white">
                    <div className="h-full flex items-center justify-center" style={bannerStyle}>
                        <h2 className="text-5xl font-black text-white font-mono bg-blue-500 p-5 px-10">
                            NAUTOBOT MARKETPLACE
                        </h2>
                    </div>
                    <hr />
                    <h1 className="text-4xl font-bold mb-5 px-5 pt-10">Top Plugins</h1>
                    <div className="px-5 flex gap-3 flex-wrap">
                        {
                            plugins.map((plugin, idx) => (
                                <MarketPlaceCard key={idx} name={plugin["name"]} />
                            ))
                        }
                    </div>

                </main>
            </div>
        </main>
    )
}
