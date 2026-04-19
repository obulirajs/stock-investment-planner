class BasePriceAdapter:
    def transform(self, raw_record: dict, symbol: str) -> dict:
        """
        Convert raw API record into the standard internal price schema.
        Must return a dict matching the internal schema.
        """
        raise NotImplementedError
