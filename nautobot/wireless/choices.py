from nautobot.core.choices import ChoiceSet


class RadioProfileChannelWidthChoices(ChoiceSet):
    WIDTH_20MHZ = 20
    WIDTH_40MHZ = 40
    WIDTH_80MHZ = 80
    WIDTH_160MHZ = 160

    CHOICES = (
        (WIDTH_20MHZ, "20 MHz"),
        (WIDTH_40MHZ, "40 MHz"),
        (WIDTH_80MHZ, "80 MHz"),
        (WIDTH_160MHZ, "160 MHz"),
    )


class RadioProfileFrequencyChoices(ChoiceSet):
    FREQUENCY_2_4G = "2.4GHz"
    FREQUENCY_5G = "5GHz"
    FREQUENCY_6G = "6GHz"

    CHOICES = (
        (FREQUENCY_2_4G, "2.4 GHz"),
        (FREQUENCY_5G, "5 GHz"),
        (FREQUENCY_6G, "6 GHz"),
    )


class SupportedDataRateStandardChoices(ChoiceSet):
    A = "802.11a"
    B = "802.11b"
    G = "802.11g"
    N = "802.11n"
    AC = "802.11ac"
    AX = "802.11ax"
    BE = "802.11be"

    CHOICES = (
        (A, "802.11a"),
        (B, "802.11b"),
        (G, "802.11g"),
        (N, "802.11n"),
        (AC, "802.11ac"),
        (AX, "802.11ax"),
        (BE, "802.11be"),
    )


class WirelessNetworkModeChoices(ChoiceSet):
    CENTRAL = "Central (tunnelMode(controller managed))"
    FABRIC = "Fabric"
    STANDALONE = "Standalone (Autonomous)"
    LOCAL = "Local (Flex)"
    MESH = "Mesh"
    BRIDGE = "Bridge"

    CHOICES = (
        (CENTRAL, "Central (tunnelMode(controller managed))"),
        (FABRIC, "Fabric"),
        (STANDALONE, "Standalone (Autonomous)"),
        (LOCAL, "Local (Flex)"),
        (MESH, "Mesh"),
        (BRIDGE, "Bridge"),
    )


class WirelessNetworkAuthenticationChoices(ChoiceSet):
    OPEN = "Open"
    WPA2_PERSONAL = "WPA2 Personal"
    WPA2_ENTERPRISE = "WPA2 Enterprise"
    ENHANCED_OPEN = "Enhanced Open"
    WPA3_PERSONAL = "WPA3 Personal"
    WPA3_SAE = "WPA3 SAE"
    WPA3_ENTERPRISE = "WPA3 Enterprise"
    WPA3_ENTERPRISE_192_BIT = "WPA3 Enterprise 192Bit"

    CHOICES = (
        (OPEN, "Open"),
        (WPA2_PERSONAL, "WPA2 Personal"),
        (WPA2_ENTERPRISE, "WPA2 Enterprise"),
        (ENHANCED_OPEN, "Enhanced Open"),
        (WPA3_PERSONAL, "WPA3 Personal"),
        (WPA3_SAE, "WPA3 SAE"),
        (WPA3_ENTERPRISE, "WPA3 Enterprise"),
        (WPA3_ENTERPRISE_192_BIT, "WPA3 Enterprise 192Bit"),
    )


class RadioProfileRegulatoryDomainChoices(ChoiceSet):
    AD = "AD"
    AE = "AE"
    AL = "AL"
    AM = "AM"
    AU = "AU"
    AR = "AR"
    AT = "AT"
    AZ = "AZ"
    BA = "BA"
    BE = "BE"
    BG = "BG"
    BH = "BH"
    BN = "BN"
    BO = "BO"
    BR = "BR"
    BS = "BS"
    BY = "BY"
    BZ = "BZ"
    CA = "CA"
    CH = "CH"
    CI = "CI"
    CL = "CL"
    CN = "CN"
    CO = "CO"
    CR = "CR"
    RS = "RS"
    CY = "CY"
    CZ = "CZ"
    DE = "DE"
    DK = "DK"
    DO = "DO"
    DZ = "DZ"
    EC = "EC"
    EE = "EE"
    EG = "EG"
    ES = "ES"
    FO = "FO"
    FI = "FI"
    FR = "FR"
    GB = "GB"
    GE = "GE"
    GI = "GI"
    GL = "GL"
    GP = "GP"
    GR = "GR"
    GT = "GT"
    GY = "GY"
    HN = "HN"
    HK = "HK"
    HR = "HR"
    HU = "HU"
    IS = "IS"
    IN = "IN"
    ID = "ID"
    IE = "IE"
    IL = "IL"
    IQ = "IQ"
    IT = "IT"
    IR = "IR"
    JM = "JM"
    JO = "JO"
    JP = "JP"
    KP = "KP"
    KR = "KR"
    KE = "KE"
    KW = "KW"
    KZ = "KZ"
    LB = "LB"
    LI = "LI"
    LK = "LK"
    LT = "LT"
    LU = "LU"
    LV = "LV"
    LY = "LY"
    MA = "MA"
    MC = "MC"
    MD = "MD"
    MK = "MK"
    MO = "MO"
    MQ = "MQ"
    MT = "MT"
    MU = "MU"
    MX = "MX"
    MY = "MY"
    NA = "NA"
    NG = "NG"
    NI = "NI"
    NL = "NL"
    NO = "NO"
    NZ = "NZ"
    OM = "OM"
    PA = "PA"
    PE = "PE"
    PL = "PL"
    PH = "PH"
    PK = "PK"
    PR = "PR"
    PT = "PT"
    PY = "PY"
    QA = "QA"
    RO = "RO"
    RU = "RU"
    SA = "SA"
    SE = "SE"
    SG = "SG"
    SI = "SI"
    SK = "SK"
    SM = "SM"
    SV = "SV"
    SY = "SY"
    TH = "TH"
    TN = "TN"
    TR = "TR"
    TT = "TT"
    TW = "TW"
    UA = "UA"
    US = "US"
    UY = "UY"
    UZ = "UZ"
    VA = "VA"
    VE = "VE"
    VI = "VI"
    VN = "VN"
    YE = "YE"
    ZA = "ZA"
    ZW = "ZW"

    CHOICES = (
        (AD, "Andorra"),
        (AE, "United Arab Emirates"),
        (AL, "Albania"),
        (AM, "Armenia"),
        (AU, "Australia"),
        (AR, "Argentina"),
        (AT, "Austria"),
        (AZ, "Azerbaijan"),
        (BA, "Bosnia and Herzegovina"),
        (BE, "Belgium"),
        (BG, "Bulgaria"),
        (BH, "Bahrain"),
        (BN, "Brunei Darussalam"),
        (BO, "Bolivia"),
        (BR, "Brazil"),
        (BS, "Bahamas"),
        (BY, "Belarus"),
        (BZ, "Belize"),
        (CA, "Canada"),
        (CH, "Switzerland"),
        (CI, "Cote d'Ivoire"),
        (CL, "Chile"),
        (CN, "China"),
        (CO, "Colombia"),
        (CR, "Costa Rica"),
        (RS, "Serbia"),
        (CY, "Cyprus"),
        (CZ, "Czech Republic"),
        (DE, "Germany"),
        (DK, "Denmark"),
        (DO, "Dominican Republic"),
        (DZ, "Algeria"),
        (EC, "Ecuador"),
        (EE, "Estonia"),
        (EG, "Egypt"),
        (ES, "Spain"),
        (FO, "Faroe Islands"),
        (FI, "Finland"),
        (FR, "France"),
        (GB, "United Kingdom"),
        (GE, "Georgia"),
        (GI, "Gibraltar"),
        (GL, "Greenland"),
        (GP, "Guadeloupe"),
        (GR, "Greece"),
        (GT, "Guatemala"),
        (GY, "Guyana"),
        (HN, "Honduras"),
        (HK, "Hong Kong"),
        (HR, "Croatia"),
        (HU, "Hungary"),
        (IS, "Iceland"),
        (IN, "India"),
        (ID, "Indonesia"),
        (IE, "Ireland"),
        (IL, "Israel"),
        (IQ, "Iraq"),
        (IT, "Italy"),
        (IR, "Iran"),
        (JM, "Jamaica"),
        (JO, "Jordan"),
        (JP, "Japan"),
        (KP, "North Korea"),
        (KR, "South Korea"),
        (KE, "Kenya"),
        (KW, "Kuwait"),
        (KZ, "Kazakhstan"),
        (LB, "Lebanon"),
        (LI, "Liechtenstein"),
        (LK, "Sri Lanka"),
        (LT, "Lithuania"),
        (LU, "Luxembourg"),
        (LV, "Latvia"),
        (LY, "Libya"),
        (MA, "Morocco"),
        (MC, "Monaco"),
        (MD, "Moldova"),
        (MK, "Macedonia"),
        (MO, "Macau"),
        (MQ, "Martinique"),
        (MT, "Malta"),
        (MU, "Mauritius"),
        (MX, "Mexico"),
        (MY, "Malaysia"),
        (NA, "Namibia"),
        (NG, "Nigeria"),
        (NI, "Nicaragua"),
        (NL, "Netherlands"),
        (NO, "Norway"),
        (NZ, "New Zealand"),
        (OM, "Oman"),
        (PA, "Panama"),
        (PE, "Peru"),
        (PL, "Poland"),
        (PH, "Philippines"),
        (PK, "Pakistan"),
        (PR, "Puerto Rico"),
        (PT, "Portugal"),
        (PY, "Paraguay"),
        (QA, "Qatar"),
        (RO, "Romania"),
        (RU, "Russia"),
        (SA, "Saudi Arabia"),
        (SE, "Sweden"),
        (SG, "Singapore"),
        (SI, "Slovenia"),
        (SK, "Slovakia"),
        (SM, "San Marino"),
        (SV, "El Salvador"),
        (SY, "Syria"),
        (TH, "Thailand"),
        (TN, "Tunisia"),
        (TR, "Turkey"),
        (TT, "Trinidad and Tobago"),
        (TW, "Taiwan"),
        (UA, "Ukraine"),
        (US, "United States"),
        (UY, "Uruguay"),
        (UZ, "Uzbekistan"),
        (VA, "Vatican City"),
        (VE, "Venezuela"),
        (VI, "Virgin Islands"),
        (VN, "Vietnam"),
        (YE, "Yemen"),
        (ZA, "South Africa"),
        (ZW, "Zimbabwe"),
    )
