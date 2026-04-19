from backend.etl.adapters.base_adapter import BasePriceAdapter


class MarketStackAdapter(BasePriceAdapter):
    def transform(self, raw_record: dict, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "date": raw_record.get("date"),
            "open": raw_record.get("open"),
            "high": raw_record.get("high"),
            "low": raw_record.get("low"),
            "close": raw_record.get("close"),
            "volume": raw_record.get("volume"),
            "adj_close": raw_record.get("adj_close") or raw_record.get("adjusted_close"),
        }
