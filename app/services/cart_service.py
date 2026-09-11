from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User


@dataclass
class CartLine:
    product: Product
    quantity: int
    line_total: int


@dataclass
class CartSummary:
    lines: list[CartLine]
    subtotal: int


async def get_or_create_cart(session: AsyncSession, user: User) -> Cart:
    stmt = select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product)).where(
        Cart.user_id == user.id
    )
    cart = (await session.execute(stmt)).scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user.id)
        # Set before add()/flush(), while `cart` is still transient: once the
        # object is persistent, SQLAlchemy no longer assumes an untouched
        # collection is empty and would lazy-load it on the next access (even
        # just to assign it), which raises MissingGreenlet under AsyncSession.
        cart.items = []
        session.add(cart)
        await session.flush()
    return cart


async def add_item(session: AsyncSession, user: User, product_id: int, quantity: int) -> CartItem:
    cart = await get_or_create_cart(session, user)
    stmt = select(CartItem).where(CartItem.cart_id == cart.user_id, CartItem.product_id == product_id)
    item = (await session.execute(stmt)).scalar_one_or_none()
    if item is None:
        item = CartItem(cart=cart, product_id=product_id, quantity=quantity)
        session.add(item)
    else:
        item.quantity += quantity
    await session.commit()
    await session.refresh(item, attribute_names=["created_at", "updated_at"])
    return item


async def set_quantity(session: AsyncSession, user: User, product_id: int, quantity: int) -> None:
    cart = await get_or_create_cart(session, user)
    item = next((i for i in cart.items if i.product_id == product_id), None)
    if item is None:
        return
    if quantity <= 0:
        cart.items.remove(item)
    else:
        item.quantity = quantity
    await session.commit()


async def remove_item(session: AsyncSession, user: User, product_id: int) -> None:
    await set_quantity(session, user, product_id, 0)


async def clear_cart(session: AsyncSession, user: User) -> None:
    cart = await get_or_create_cart(session, user)
    cart.items.clear()
    await session.commit()


async def get_summary(session: AsyncSession, user: User) -> CartSummary:
    cart = await get_or_create_cart(session, user)
    lines: list[CartLine] = []
    subtotal = 0
    for item in cart.items:
        line_total = item.product.price * item.quantity
        subtotal += line_total
        lines.append(CartLine(product=item.product, quantity=item.quantity, line_total=line_total))
    return CartSummary(lines=lines, subtotal=subtotal)
