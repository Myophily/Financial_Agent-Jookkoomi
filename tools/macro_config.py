# tools/macro_config.py
# FRED Economic Indicators Configuration for Macroeconomic Analysis

"""
Configuration file for FRED (Federal Reserve Economic Data) indicators.
Contains 28 economic indicators across multiple categories for comprehensive macro analysis.
"""

FRED_INDICATORS = [
    # ========== GDP Growth ==========
    {
        "category": "GDP",
        "name": "Real GDP",
        "series_id": "GDPC1",
        "description": "Real Gross Domestic Product (Quarterly)"
    },
    {
        "category": "GDP",
        "name": "Nominal GDP",
        "series_id": "GDP",
        "description": "Gross Domestic Product (Quarterly)"
    },

    # ========== Inflation ==========
    {
        "category": "Inflation",
        "name": "CPI (Consumer Price Index)",
        "series_id": "CPIAUCSL",
        "description": "Consumer Price Index for All Urban Consumers: All Items"
    },
    {
        "category": "Inflation",
        "name": "PPI (Producer Price Index)",
        "series_id": "PPIACO",
        "description": "Producer Price Index for All Commodities"
    },
    {
        "category": "Inflation",
        "name": "Core PCE (Personal Consumption Expenditures)",
        "series_id": "PCEPILFE",
        "description": "Personal Consumption Expenditures Excluding Food and Energy"
    },
    {
        "category": "Inflation",
        "name": "Expected Inflation (U of Michigan)",
        "series_id": "MICH",
        "description": "University of Michigan 1-Year Expected Inflation"
    },

    # ========== Employment ==========
    {
        "category": "Employment",
        "name": "Unemployment Rate",
        "series_id": "UNRATE",
        "description": "Unemployment Rate (Monthly)"
    },
    {
        "category": "Employment",
        "name": "Nonfarm Payrolls",
        "series_id": "PAYEMS",
        "description": "All Employees: Total Nonfarm Payrolls (Thousands)"
    },

    # ========== Manufacturing/Production ==========
    {
        "category": "Manufacturing",
        "name": "Industrial Production Index",
        "series_id": "INDPRO",
        "description": "Industrial Production Index"
    },
    {
        "category": "Manufacturing",
        "name": "Capacity Utilization",
        "series_id": "TCU",
        "description": "Capacity Utilization: Total Industry"
    },

    # ========== Consumer/Sales ==========
    {
        "category": "Consumer",
        "name": "Retail Sales",
        "series_id": "RSAFS",
        "description": "Retail and Food Services Sales (Millions)"
    },
    {
        "category": "Consumer",
        "name": "Durable Goods Orders",
        "series_id": "DGORDER",
        "description": "Manufacturers' New Orders: Durable Goods (Millions)"
    },

    # ========== Interest Rates & Monetary ==========
    {
        "category": "Interest Rates",
        "name": "Federal Funds Rate",
        "series_id": "FEDFUNDS",
        "description": "Federal Funds Effective Rate"
    },
    {
        "category": "Interest Rates",
        "name": "10-Year Treasury Yield",
        "series_id": "DGS10",
        "description": "10-Year Treasury Constant Maturity Rate"
    },
    {
        "category": "Interest Rates",
        "name": "2-Year Treasury Yield",
        "series_id": "DGS2",
        "description": "2-Year Treasury Constant Maturity Rate"
    },
    {
        "category": "Interest Rates",
        "name": "Yield Spread (10Y-2Y)",
        "series_id": "T10Y2Y",
        "description": "10-Year Treasury Minus 2-Year Treasury Spread"
    },

    # ========== Market Sentiment/Liquidity ==========
    {
        "category": "Market Sentiment",
        "name": "VIX (Volatility Index)",
        "series_id": "VIXCLS",
        "description": "CBOE Volatility Index: VIX"
    },
    {
        "category": "Market Sentiment",
        "name": "M2 Money Supply",
        "series_id": "M2SL",
        "description": "M2 Money Stock (Billions)"
    },

    # ========== Leading Indicator - Housing ==========
    {
        "category": "Housing",
        "name": "Housing Starts",
        "series_id": "HOUST",
        "description": "Housing Starts: Total New Privately Owned (Thousands)"
    },

    # ========== Corporate Profits ==========
    {
        "category": "Corporate",
        "name": "After-Tax Corporate Profits",
        "series_id": "CP",
        "description": "Corporate Profits After Tax (Billions)"
    },

    # ========== Inflation Expectations ==========
    {
        "category": "Inflation Expectations",
        "name": "10-Year Expected Inflation",
        "series_id": "T10YIE",
        "description": "10-Year Breakeven Inflation Rate"
    },

    # ========== Credit Risk ==========
    {
        "category": "Credit Risk",
        "name": "High Yield Bond Spread",
        "series_id": "BAMLH0A0HYM2",
        "description": "ICE BofA US High Yield Index Option-Adjusted Spread"
    },

    # ========== Consumer Sentiment ==========
    {
        "category": "Consumer Sentiment",
        "name": "U of Michigan Consumer Sentiment",
        "series_id": "UMCSENT",
        "description": "University of Michigan Consumer Sentiment Index"
    },

    # ========== Korea Indicators (OECD) ==========
    {
        "category": "Korea (OECD)",
        "name": "Korea GDP",
        "source": "ECOS",
        "stat_code": "902Y016",
        "item_code": "KOR",
        "cycle": "A",
        "description": "Gross Domestic Product (Million USD, Annual)"
    },
    {
        "category": "Korea (OECD)",
        "name": "Korea CPI",
        "source": "ECOS",
        "stat_code": "901Y009",
        "item_code": "0",
        "cycle": "M",
        "description": "Consumer Price Index (Total Index, 2020=100)"
    },
    {
        "category": "Korea (OECD)",
        "name": "Korea PPI",
        "source": "ECOS",
        "stat_code": "404Y014",
        "item_code": "*AA",
        "cycle": "M",
        "description": "Producer Price Index (Total Index, 2020=100)"
    },

    # ========== Global Indicators ==========
    {
        "category": "Global",
        "name": "Eurozone HICP",
        "series_id": "CP0000EZ19M086NEST",
        "description": "Harmonized Index of Consumer Prices for Euro Area"
    },
]

# Category priority for Korean stocks (numeric ticker)
KOREA_PRIORITY_CATEGORIES = [
    "Korea (OECD)",
    "Global",
    "Interest Rates",
    "Inflation",
    "GDP",
    "Employment",
    "Manufacturing",
    "Consumer",
    "Market Sentiment",
    "Credit Risk",
    "Housing",
    "Corporate",
    "Inflation Expectations",
    "Consumer Sentiment"
]

# Category priority for US stocks (alphabetic ticker)
US_PRIORITY_CATEGORIES = [
    "GDP",
    "Employment",
    "Inflation",
    "Manufacturing",
    "Consumer",
    "Interest Rates",
    "Market Sentiment",
    "Credit Risk",
    "Housing",
    "Corporate",
    "Inflation Expectations",
    "Consumer Sentiment",
    "Korea (OECD)",
    "Global"
]

# ========== GLOBAL ENVIRONMENT TOOL CONFIGURATION ==========

# World Bank Indicators (5 indicators × 5 countries = 25 data points)
WORLD_BANK_INDICATORS = [
    {
        "name": "GDP Growth Rate",
        "symbol": "NY.GDP.MKTP.KD.ZG",
        "description": "GDP growth (annual %)"
    },
    {
        "name": "Inflation",
        "symbol": "FP.CPI.TOTL.ZG",
        "description": "Inflation, consumer prices (annual %)"
    },
    {
        "name": "Unemployment Rate",
        "symbol": "SL.UEM.TOTL.ZS",
        "description": "Unemployment, total (% of labor force)"
    },
    {
        "name": "Real Interest Rate",
        "symbol": "FR.INR.RINR",
        "description": "Real interest rate (%)"
    },
    {
        "name": "Current Account Balance",
        "symbol": "BN.CAB.XOKA.GD.ZS",
        "description": "Current account balance (% of GDP)"
    }
]

# Global FRED Indicators (comprehensive set for global analysis)
GLOBAL_FRED_INDICATORS = [
    # Major Indicators - Interest Rates
    {"category": "Interest Rates", "name": "US Federal Funds Rate", "series_id": "FEDFUNDS"},
    {"category": "Interest Rates", "name": "US 10-Year Treasury", "series_id": "DGS10"},
    {"category": "Interest Rates", "name": "US 2-Year Treasury", "series_id": "DGS2"},
    {"category": "Interest Rates", "name": "Yield Spread", "series_id": "T10Y2Y"},

    # Liquidity
    {"category": "Liquidity", "name": "M2 Money Supply", "series_id": "M2SL"},

    # Market Sentiment
    {"category": "Market Sentiment", "name": "VIX Index", "series_id": "VIXCLS"},

    # Exchange Rates
    {"category": "Exchange Rates", "name": "US Dollar Index", "series_id": "DTWEXBGS"},
    {"category": "Exchange Rates", "name": "KRW/USD Exchange Rate", "series_id": "DEXKOUS"},
    {"category": "Exchange Rates", "name": "JPY/USD Exchange Rate", "series_id": "DEXJPUS"},

    # Inflation Expectations
    {"category": "Inflation Expectations", "name": "10-Year Expected Inflation", "series_id": "T10YIE"},

    # OECD Interest Rates
    {"category": "Global Interest Rates", "name": "Eurozone Short-Term Rate", "series_id": "IRSTCI01EZM156N"},
    {"category": "Global Interest Rates", "name": "Japan Short-Term Rate", "series_id": "IRSTCI01JPM156N"},

    # Market Analysis - Credit Risk
    {"category": "Credit Risk", "name": "High Yield Bond Spread", "series_id": "BAMLH0A0HYM2"},

    # Central Bank Policy
    {"category": "Central Bank", "name": "Fed Total Assets", "series_id": "WALCL"},

    # Commodities
    {"category": "Commodities", "name": "WTI Crude Oil", "series_id": "DCOILWTICO"},

    # Consumer Sentiment
    {"category": "Consumer Sentiment", "name": "U of Michigan Consumer Sentiment", "series_id": "UMCSENT"}
]

# Global Market Indices
MARKET_INDICES = [
    {"name": "S&P 500", "symbol": "^GSPC", "region": "US"},
    {"name": "NASDAQ", "symbol": "^IXIC", "region": "US"},
    {"name": "KOSPI", "symbol": "^KS11", "region": "KR"},
    {"name": "Nikkei 225", "symbol": "^N225", "region": "JP"}
]

# Country codes for World Bank data
COUNTRY_CODES = {
    'US': 'United States',
    'CN': 'China',
    'JP': 'Japan',
    'KR': 'Korea',
    'DE': 'Germany (Eurozone)'
}

# Country priority for Korean vs US stocks
KOREA_PRIORITY_COUNTRIES = ['KR', 'CN', 'JP', 'US', 'DE']
US_PRIORITY_COUNTRIES = ['US', 'CN', 'JP', 'KR', 'DE']

# ========== POLICY & SECTOR ENVIRONMENT TOOL CONFIGURATION ==========

POLICY_ENVIRONMENT_CONFIG = {
    "section_1_policy_info": {
        "subsections": {
            "monetary_policy": {
                "display_name": "Monetary Policy",
                "indicators": [
                    {"series_id": "FEDFUNDS", "name": "Federal Funds Rate"},
                    {"series_id": "DGS10", "name": "10-Year Treasury"},
                    {"series_id": "DGS2", "name": "2-Year Treasury"},
                    {"series_id": "T10Y2Y", "name": "Yield Spread"},
                    {"series_id": "M2SL", "name": "M2 Money Supply"},
                    {"series_id": "WALCL", "name": "Fed Total Assets"}
                ]
            },
            "fiscal_policy": {
                "display_name": "Fiscal Policy",
                "indicators": [
                    {"series_id": "CPIAUCSL", "name": "Consumer Price Index"},
                    {"series_id": "CPILFESL", "name": "Core CPI"},
                    {"series_id": "PCEPI", "name": "PCE Price Index"},
                    {"series_id": "GDP", "name": "Nominal GDP"},
                    {"series_id": "GDPC1", "name": "Real GDP"}
                ]
            },
            "market_impact": {
                "display_name": "Market Impact",
                "indicators": [
                    {"series_id": "VIXCLS", "name": "VIX Volatility Index"}
                ]
            },
            "forward_looking": {
                "display_name": "Forward-Looking Indicators",
                "indicators": [
                    {"series_id": "T10YIE", "name": "10-Year Expected Inflation"},
                    {"series_id": "T5YIE", "name": "5-Year Expected Inflation"},
                    {"series_id": "BAMLH0A0HYM2", "name": "High Yield Bond Spread"}
                ]
            },
            "housing_household": {
                "display_name": "Housing & Household",
                "indicators": [
                    {"series_id": "MORTGAGE30US", "name": "30-Year Mortgage Rate"},
                    {"series_id": "TDSP", "name": "Household Debt Service Ratio"}
                ]
            }
        }
    },
    "section_2_social_demographic": {
        "subsections": {
            "demographics": {
                "display_name": "Demographics",
                "indicators": [
                    {
                        "source": "WorldBank",
                        "symbol": "SP.POP.TOTL",
                        "name": "Total Population",
                        "countries": ["US"]
                    },
                    {
                        "source": "FRED",
                        "series_id": "LFWA64TTUSM647S",
                        "name": "Working-Age Population"
                    }
                ]
            },
            "labor_consumer": {
                "display_name": "Labor & Consumer Behavior",
                "indicators": [
                    {"series_id": "UNRATE", "name": "Unemployment Rate"},
                    {"series_id": "CIVPART", "name": "Labor Force Participation Rate"},
                    {"series_id": "RSXFS", "name": "Retail Sales"},
                    {"series_id": "PSAVERT", "name": "Personal Saving Rate"},
                    {"series_id": "CSUSHPISA", "name": "House Price Index"},
                    {"series_id": "HOUST", "name": "Housing Starts"}
                ]
            }
        }
    },
    "section_3_sector_impact": {
        "etfs": [
            {"symbol": "XLK", "name": "Technology"},
            {"symbol": "XLE", "name": "Energy"},
            {"symbol": "XLV", "name": "Healthcare"},
            {"symbol": "XLP", "name": "Consumer Staples"}
        ]
    }
}

# ========== ECONOMIC CYCLE DASHBOARD CONFIGURATION ==========

ECONOMIC_CYCLE_CONFIG = {
    "group_a_liquidity_rates": {
        "display_name": "A. Money Supply, Interest Rates & Liquidity",
        "indicators": [
            {"series_id": "M2SL", "name": "M2 Money Supply (US)", "source": "FRED"},
            {"series_id": "FEDFUNDS", "name": "US Federal Funds Rate", "source": "FRED"},
            {"series_id": "T10Y2Y", "name": "Yield Spread (10Y-2Y)", "source": "FRED"}
        ],
        "ecos_indicators": {
            "money_supply": {
                "stat_code": "101Y009",
                "item_code": "BBAALA",
                "cycle": "M",
                "name": "Korea Money Supply (M2)"
            },
            "base_rate": {
                "stat_code": "722Y001",
                "item_code": "0101000",
                "cycle": "D",
                "name": "Korea Base Rate"
            }
        }
    },
    "group_b_real_economy": {
        "display_name": "B. Real Economy & Inflation",
        "indicators": [
            {"series_id": "GDP", "name": "GDP (US)", "source": "FRED"},
            {"series_id": "INDPRO", "name": "Industrial Production Index (US)", "source": "FRED"},
            {"series_id": "CPIAUCSL", "name": "Consumer Price Index (US)", "source": "FRED"},
            {"series_id": "UNRATE", "name": "Unemployment Rate (US)", "source": "FRED"}
        ],
        "ecos_indicators": {
            "gdp": {
                "stat_code": "902Y016",
                "item_code": "KOR",
                "cycle": "A",
                "name": "Korea GDP",
                "data_points": 10
            },
            "cpi": {
                "stat_code": "901Y009",
                "item_code": "0",
                "cycle": "M",
                "name": "Korea Consumer Price Index",
                "data_points": 24
            },
            "ppi": {
                "stat_code": "404Y014",
                "item_code": "*AA",
                "cycle": "M",
                "name": "Korea Producer Price Index",
                "data_points": 24
            },
            "unemployment": {
                "stat_code": "901Y027",
                "item_codes": [
                    {"code": "I61BC/I28A", "name": "Unemployed"},
                    {"code": "I61BC/I28B", "name": "Unemployment Rate"}
                ],
                "cycle": "M",
                "name": "Korea Employment",
                "data_points": 24,
                "multi_item": True
            },
            "consumer_sentiment": {
                "stat_code": "511Y002",
                "item_code": "FME/99988",
                "cycle": "M",
                "name": "Consumer Sentiment Index",
                "data_points": 24
            },
            "business_sentiment": {
                "stat_code": "512Y007",
                "item_codes": [
                    {"code": "AA", "name": "All Industries"},      # Try without /99988 suffix
                    {"code": "AM", "name": "Manufacturing"},
                    {"code": "AG", "name": "Non-Manufacturing"},
                    {"code": "AD", "name": "Construction"}
                ],
                "cycle": "M",
                "name": "Business Survey Index",
                "data_points": 24,
                "multi_item": True
            }
        }
    },
    "group_c_risk_credit": {
        "display_name": "C. Risk, Credit & Debt",
        "indicators": [
            {"series_id": "^VIX", "name": "VIX Index (Fear Index)", "source": "yfinance"},
            {"series_id": "BAMLH0A0HYM2", "name": "High Yield Spread (Corporate Credit)", "source": "FRED"},
            {"series_id": "TDSP", "name": "Household Debt Service Ratio", "source": "FRED"},
            {"series_id": "DRBLACBS", "name": "Commercial Bank Loan Delinquency Rate", "source": "FRED"}
        ],
        "ecos_indicators": {
            "household_debt": {
                "stat_code": "151Y004",
                "item_code": "1000000",
                "cycle": "Q",
                "name": "Korea Household Debt"
            },
            "corporate_debt": {
                "stat_code": "131Y017",
                "item_code": "BDDF1",
                "item_codes": ["A", "B"],  # A=facility funds, B=operating funds
                "cycle": "Q",
                "name": "Korea Corporate Debt",
                "aggregation_required": True
            }
        }
    },
    "group_d_market_assets": {
        "display_name": "D. Market Indices & Asset Prices",
        "indicators": [
            {"symbol": "^GSPC", "name": "S&P 500 (US)", "source": "yfinance"},
            {"symbol": "^KS11", "name": "KOSPI (Korea)", "source": "yfinance"},
            {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "source": "yfinance"},
            {
                "type": "composite_ratio",
                "name": "Copper/Gold Ratio (Dr. Copper)",
                "numerator": "HG=F",
                "denominator": "GC=F",
                "source": "yfinance"
            }
        ]
    }
}
