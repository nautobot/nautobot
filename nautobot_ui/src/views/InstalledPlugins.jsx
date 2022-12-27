import ListTemplate from "@nautobot/layouts/ListTemplate";

export default function InstalledPlugins(){
    return (
        <ListTemplate
            page_title={"Installed Plugins"}
            table_head_url="plugins/installed-plugins/table-fields/"
            table_data_url="plugins/installed-plugins/"
            buttons={[
                {"icon": "home", "tooltip": "Plugin home"},
                {"icon": "cog", "tooltip": "Settings"},
                {"icon": "book", "tooltip": "Plugin details"},
            ]}
        />
    )
}