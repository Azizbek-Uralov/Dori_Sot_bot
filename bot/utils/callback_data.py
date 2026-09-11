from aiogram.filters.callback_data import CallbackData


class LangCB(CallbackData, prefix="lang"):
    code: str


class SubCheckCB(CallbackData, prefix="subcheck"):
    pass


class CategoryCB(CallbackData, prefix="cat"):
    id: int


class ProductCB(CallbackData, prefix="prod"):
    id: int


class AddToCartCB(CallbackData, prefix="add2cart"):
    product_id: int


class CartItemCB(CallbackData, prefix="cartitem"):
    product_id: int
    action: str  # "inc" | "dec" | "remove"


class ZoneCB(CallbackData, prefix="zone"):
    id: int


class OrderConfirmCB(CallbackData, prefix="ordconf"):
    action: str  # "confirm" | "cancel"
