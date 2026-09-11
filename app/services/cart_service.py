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
        session.add(cart)
        await session.flush()
        cart.items = []
    return cart


async def add_item(session: AsyncSession, user: User, product_id: int, quantity: int) -> CartItem:
    cart = await get_or_create_cart(session, user)
    stmt = select(CartItem).where(CartItem.cart_id == cart.user_id, CartItem.product_id == product_id)
    item = (await session.execute(stmt)).scalar_one_or_none()
    if item is None:
        item = CartItem(cart_id=cart.user_id, product_id=product_id, quantity=quantity)
        session.add(item)
    else:
        item.quantity += quantity
    await session.commit()
    await session.refresh(item)
    return item


async def set_quantity(session: AsyncSession, user: User, product_id: int, quantity: int) -> None:
    cart = await get_or_create_cart(session, user)
    stmt = select(CartItem).where(CartItem.cart_id == cart.user_id, CartItem.product_id == product_id)
    item = (await session.execute(stmt)).scalar_one_or_none()
    if item is None:
        return
    if quantity <= 0:
        await session.delete(item)
    else:
        item.quantity = quantity
    await session.commit()


async def remove_item(session: AsyncSession, user: User, product_id: int) -> None:
    await set_quantity(session, user, product_id, 0)


async def clear_cart(session: AsyncSession, user: User) -> None:
    cart = await get_or_create_cart(session, user)
    for item in list(cart.items):
        await session.delete(item)
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
