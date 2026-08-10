"""
🌐 طبقة البيانات — جلب الأسعار
"""
class DataLayer:
    async def get_price(self, coin: str):
        # مؤقت — نعيد سعر ثابت حتى نربط API حقيقي
        return {"price": 65000.0}

data_layer = DataLayer()
