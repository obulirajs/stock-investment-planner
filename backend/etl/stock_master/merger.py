# backend/etl/stock_master/merger.py
def merge(nse_item: dict, fmp_profile: dict) -> dict:
    """
    Merge NSE base item and FMP profile into the standardized stocks_master document.
    Priority: FMP profile (if available) > NSE fields.
    """
    doc = {}
    symbol = nse_item.get("symbol")
    doc["symbol"] = symbol

    # Name
    name = None
    if fmp_profile:
        name = fmp_profile.get("companyName") or fmp_profile.get("company")
    doc["name"] = name or nse_item.get("symbol")

    # Sector / Industry
    doc["sector"] = (fmp_profile.get("sector") if fmp_profile else None) or nse_item.get("sector")
    doc["industry"] = (fmp_profile.get("industry") if fmp_profile else None) or nse_item.get("industry")

    # Market cap (FMP returns marketCap)
    market_cap = None
    if fmp_profile:
        market_cap = fmp_profile.get("mktCap") or fmp_profile.get("marketCap") or fmp_profile.get("marketcap") or fmp_profile.get("marketCap")
    # try other keys too
    doc["market_cap"] = market_cap or nse_item.get("marketCap")

    metadata = {}
    if fmp_profile:
        metadata["pe_ratio"] = fmp_profile.get("pe") or fmp_profile.get("peRatio") or fmp_profile.get("priceEarningsRatio")
        metadata["eps"] = fmp_profile.get("eps")
        metadata["beta"] = fmp_profile.get("beta")
        metadata["price"] = fmp_profile.get("price")
        metadata["website"] = fmp_profile.get("website")
        metadata["description"] = fmp_profile.get("description") or fmp_profile.get("longBusinessSummary")
        metadata["fmp_raw"] = fmp_profile  # store raw profile for debugging
        metadata["week_52_high"] = fmp_profile.get("range52WeekHigh") or fmp_profile.get("52WeekHigh") or fmp_profile.get("yearHigh")
        metadata["week_52_low"] = fmp_profile.get("range52WeekLow") or fmp_profile.get("52WeekLow") or fmp_profile.get("yearLow")
    else:
        metadata["fmp_raw"] = None

    # keep source flags
    metadata["sources"] = {"nse": True, "fmp": bool(fmp_profile)}

    doc["metadata"] = metadata

    return doc
