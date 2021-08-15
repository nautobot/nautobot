 django_tables2  tables

 nautobot.dcim.models  Region, Site
 nautobot.extras.tables  StatusTableMixin
 nautobot.tenancy.tables  TenantColumn
 nautobot.utilities.tables  
    BaseTable
    ButtonsColumn
    TagColumn
    ToggleColumn

     .template_code       MPTT_LINK

  all
    RegionTable
    SiteTable



#
# Regions
#


      RegionTable(BaseTable)
    pk   ToggleColumn()
    name   tables.TemplateColumn(template_code=MPTT_LINK, orderable=False, attrs={"td": {"class": "text-nowrap"}})
    site_count   tables.Column(verbose_name="Sites")
    actions   ButtonsColumn(Region)

          Meta(BaseTable.Meta)
        model   Region
        fields   ("pk", "name", "slug", "site_count", "description", "actions")
        default_columns   ("pk", "name", "site_count", "description", "actions")


#
# Sites
#


     SiteTable(StatusTableMixin, BaseTable):
    pk   ToggleColumn()
    name   tables.LinkColumn(order_by=("_name",))
    region   tables.Column(linkify=True)
    tenant   TenantColumn()
    tags   TagColumn(url_name="dcim:site_list")

         Meta(BaseTable.Meta):
        model   Site
        fields  
            pk
            name
            slug
            status
            facility
            region
            tenant
            asn
            time_zone
            description
            physical_address
            shipping_address
            latitude
            longitude
            contact_name
            contact_phone
            contact_email
            tags
        
        default_columns  
             pk
             name
             status
             facility
             region
             tenant
             asn
             description
        
