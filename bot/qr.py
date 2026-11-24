import base64
import io

import qrcode
from pytoniq_core import Address, begin_cell


def valid_addr(a: str) -> bool:
    try:
        Address(a.strip())
        return True
    except Exception:
        return False


def _bounce(a: str) -> str:
    """UQ -> EQ: при сбое гифт вернётся, а не улетит в никуда."""
    return Address(a.strip()).to_str(
        is_user_friendly=True, is_bounceable=True, is_url_safe=True)


def nft_body(new_owner: str, response: str) -> str:
    cell = (begin_cell()
            .store_uint(0x5FCC3D14, 32).store_uint(0, 64)
            .store_address(Address(_bounce(new_owner)))
            .store_address(Address(_bounce(response)))
            .store_uint(0, 1).store_coins(1).store_uint(0, 1)
            .end_cell())
    return base64.urlsafe_b64encode(cell.to_boc(False)).decode()


def link(dest: str, amount_ton: float, body: str | None = None) -> str:
    url = f"ton://transfer/{dest}?amount={int(round(amount_ton * 1e9))}"
    return url + (f"&bin={body}" if body else "")


def qr_png(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((img.pixel_size * 3, img.pixel_size * 3))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
