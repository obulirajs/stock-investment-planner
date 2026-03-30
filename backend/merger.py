# backend/merger.py
def merge_marketstack_screener(ms_item: dict, screener: dict) -> dict:
    """
    Normalize Marketstack ticker (ms_item) + screener data -> stocks_master document.
    """
    doc = {}
    # symbol normalization (Marketstack uses 'TCS.XNSE')
    symbol = (ms_item.get("symbol") or ms_item.get("ticker") or "")
    if symbol and "." in symbol:
        symbol_only = symbol.split(".")[0]
    else:
        symbol_only = symbol
    doc["symbol"] = symbol_only

    doc["name"] = ms_item.get("name") or ms_item.get("company_name") or symbol_only
    # basic fields
    doc["market_cap"] = ms_item.get("market_cap") or screener.get("market_cap")
    doc["sector"] = screener.get("sector") or ms_item.get("industry") or None
    doc["industry"] = screener.get("industry") or None

    metadata = {}
    # latest price fields if present in ms_item (some endpoints include 'last' or 'close')
    metadata["latest_price"] = ms_item.get("close") or ms_item.get("last") or None
    metadata["52w_high"] = ms_item.get("high") or ms_item.get("52_week_high")
    metadata["52w_low"] = ms_item.get("low") or ms_item.get("52_week_low")

    # fundamentals from screener
    metadata["pe"] = screener.get("pe")
    metadata["pb"] = screener.get("pb")
    metadata["summary"] = screener.get("summary")
    metadata["sources"] = {"marketstack": True, "screener": bool(screener)}
    doc["metadata"] = metadata

    return doc
