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
    CENTRAL = "Central"
    FABRIC = "Fabric"
    STANDALONE = "Standalone (Autonomous)"
    LOCAL = "Local (Flex)"
    MESH = "Mesh"
    BRIDGE = "Bridge"

    CHOICES = (
        (CENTRAL, "Central"),
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
        (AD, "Andorra (AD)"),
        (AE, "United Arab Emirates (AE)"),
        (AL, "Albania (AL)"),
        (AM, "Armenia (AM)"),
        (AU, "Australia (AU)"),
        (AR, "Argentina (AR)"),
        (AT, "Austria (AT)"),
        (AZ, "Azerbaijan (AZ)"),
        (BA, "Bosnia and Herzegovina (BA)"),
        (BE, "Belgium (BE)"),
        (BG, "Bulgaria (BG)"),
        (BH, "Bahrain (BH)"),
        (BN, "Brunei Darussalam (BN)"),
        (BO, "Bolivia (BO)"),
        (BR, "Brazil (BR)"),
        (BS, "Bahamas (BS)"),
        (BY, "Belarus (BY)"),
        (BZ, "Belize (BZ)"),
        (CA, "Canada (CA)"),
        (CH, "Switzerland (CH)"),
        (CI, "Cote d'Ivoire (CI)"),
        (CL, "Chile (CL)"),
        (CN, "China (CN)"),
        (CO, "Colombia (CO)"),
        (CR, "Costa Rica (CR)"),
        (RS, "Serbia (RS)"),
        (CY, "Cyprus (CY)"),
        (CZ, "Czech Republic (CZ)"),
        (DE, "Germany (DE)"),
        (DK, "Denmark (DK)"),
        (DO, "Dominican Republic (DO)"),
        (DZ, "Algeria (DZ)"),
        (EC, "Ecuador (EC)"),
        (EE, "Estonia (EE)"),
        (EG, "Egypt (EG)"),
        (ES, "Spain (ES)"),
        (FO, "Faroe Islands (FO)"),
        (FI, "Finland (FI)"),
        (FR, "France (FR)"),
        (GB, "United Kingdom (GB)"),
        (GE, "Georgia (GE)"),
        (GI, "Gibraltar (GI)"),
        (GL, "Greenland (GL)"),
        (GP, "Guadeloupe (GP)"),
        (GR, "Greece (GR)"),
        (GT, "Guatemala (GT)"),
        (GY, "Guyana (GY)"),
        (HN, "Honduras (HN)"),
        (HK, "Hong Kong (HK)"),
        (HR, "Croatia (HR)"),
        (HU, "Hungary (HU)"),
        (IS, "Iceland (IS)"),
        (IN, "India (IN)"),
        (ID, "Indonesia (ID)"),
        (IE, "Ireland (IE)"),
        (IL, "Israel (IL)"),
        (IQ, "Iraq (IQ)"),
        (IT, "Italy (IT)"),
        (IR, "Iran (IR)"),
        (JM, "Jamaica (JM)"),
        (JO, "Jordan (JO)"),
        (JP, "Japan (JP)"),
        (KP, "North Korea (KP)"),
        (KR, "South Korea (KR)"),
        (KE, "Kenya (KE)"),
        (KW, "Kuwait (KW)"),
        (KZ, "Kazakhstan (KZ)"),
        (LB, "Lebanon (LB)"),
        (LI, "Liechtenstein (LI)"),
        (LK, "Sri Lanka (LK)"),
        (LT, "Lithuania (LT)"),
        (LU, "Luxembourg (LU)"),
        (LV, "Latvia (LV)"),
        (LY, "Libya (LY)"),
        (MA, "Morocco (MA)"),
        (MC, "Monaco (MC)"),
        (MD, "Moldova (MD)"),
        (MK, "Macedonia (MK)"),
        (MO, "Macau (MO)"),
        (MQ, "Martinique (MQ)"),
        (MT, "Malta (MT)"),
        (MU, "Mauritius (MU)"),
        (MX, "Mexico (MX)"),
        (MY, "Malaysia (MY)"),
        (NA, "Namibia (NA)"),
        (NG, "Nigeria (NG)"),
        (NI, "Nicaragua (NI)"),
        (NL, "Netherlands (NL)"),
        (NO, "Norway (NO)"),
        (NZ, "New Zealand (NZ)"),
        (OM, "Oman (OM)"),
        (PA, "Panama (PA)"),
        (PE, "Peru (PE)"),
        (PL, "Poland (PL)"),
        (PH, "Philippines (PH)"),
        (PK, "Pakistan (PK)"),
        (PR, "Puerto Rico (PR)"),
        (PT, "Portugal (PT)"),
        (PY, "Paraguay (PY)"),
        (QA, "Qatar (QA)"),
        (RO, "Romania (RO)"),
        (RU, "Russia (RU)"),
        (SA, "Saudi Arabia (SA)"),
        (SE, "Sweden (SE)"),
        (SG, "Singapore (SG)"),
        (SI, "Slovenia (SI)"),
        (SK, "Slovakia (SK)"),
        (SM, "San Marino (SM)"),
        (SV, "El Salvador (SV)"),
        (SY, "Syria (SY)"),
        (TH, "Thailand (TH)"),
        (TN, "Tunisia (TN)"),
        (TR, "Turkey (TR)"),
        (TT, "Trinidad and Tobago (TT)"),
        (TW, "Taiwan (TW)"),
        (UA, "Ukraine (UA)"),
        (US, "United States (US)"),
        (UY, "Uruguay (UY)"),
        (UZ, "Uzbekistan (UZ)"),
        (VA, "Vatican City (VA)"),
        (VE, "Venezuela (VE)"),
        (VI, "Virgin Islands (VI)"),
        (VN, "Vietnam (VN)"),
        (YE, "Yemen (YE)"),
        (ZA, "South Africa (ZA)"),
        (ZW, "Zimbabwe (ZW)"),
    )
