"""
payment.py - Tích hợp thanh toán VNPay và MoMo
"""

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime
from urllib.parse import urlencode, quote_plus

import requests


# ============================================================
#  VNPAY
# ============================================================

VNPAY_TMN_CODE   = os.environ.get("VNPAY_TMN_CODE", "")
VNPAY_HASH_SECRET = os.environ.get("VNPAY_HASH_SECRET", "")
VNPAY_URL        = os.environ.get("VNPAY_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
VNPAY_RETURN_URL = os.environ.get("VNPAY_RETURN_URL", "http://localhost:5000/payment/vnpay/return")


def vnpay_create_payment_url(order_id, amount, order_info, client_ip):
    """
    Tạo URL thanh toán VNPay.
    amount: số tiền VND (VNPay nhân x100 → truyền amount*100)
    Trả về URL redirect sang cổng VNPay.
    """
    vnp_params = {
        "vnp_Version":    "2.1.0",
        "vnp_Command":    "pay",
        "vnp_TmnCode":    VNPAY_TMN_CODE,
        "vnp_Amount":     str(int(amount) * 100),
        "vnp_CurrCode":   "VND",
        "vnp_TxnRef":     str(order_id),
        "vnp_OrderInfo":  order_info,
        "vnp_OrderType":  "other",
        "vnp_Locale":     "vn",
        "vnp_ReturnUrl":  VNPAY_RETURN_URL,
        "vnp_IpAddr":     client_ip,
        "vnp_CreateDate": datetime.now().strftime("%Y%m%d%H%M%S"),
    }

    # Sắp xếp params theo thứ tự alphabet (bắt buộc của VNPay)
    sorted_params = sorted(vnp_params.items())

    # Tạo chuỗi query để hash
    hash_data = "&".join(f"{k}={quote_plus(str(v), safe='')}" for k, v in sorted_params)

    # HMAC-SHA512
    secure_hash = hmac.new(
        VNPAY_HASH_SECRET.encode("utf-8"),
        hash_data.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()

    # Build URL cuối
    query_string = "&".join(f"{k}={quote_plus(str(v), safe='')}" for k, v in sorted_params)
    payment_url = f"{VNPAY_URL}?{query_string}&vnp_SecureHash={secure_hash}"

    return payment_url


def vnpay_verify_return(params):
    """
    Xác thực chữ ký khi VNPay redirect về.
    Trả về (is_valid: bool, response_code: str, order_id: str)
    """
    vnp_secure_hash = params.get("vnp_SecureHash", "")
    response_code   = params.get("vnp_ResponseCode", "")
    order_id        = params.get("vnp_TxnRef", "")

    # Lấy tất cả params trừ vnp_SecureHash và vnp_SecureHashType
    verify_params = {
        k: v for k, v in params.items()
        if k not in ("vnp_SecureHash", "vnp_SecureHashType")
    }

    sorted_params = sorted(verify_params.items())
    hash_data = "&".join(f"{k}={quote_plus(str(v), safe='')}" for k, v in sorted_params)

    expected_hash = hmac.new(
        VNPAY_HASH_SECRET.encode("utf-8"),
        hash_data.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()

    is_valid = hmac.compare_digest(expected_hash.lower(), vnp_secure_hash.lower())
    return is_valid, response_code, order_id


VNPAY_RESPONSE_CODES = {
    "00": "Giao dịch thành công",
    "07": "Trừ tiền thành công nhưng giao dịch bị nghi ngờ",
    "09": "Thẻ/Tài khoản chưa đăng ký dịch vụ InternetBanking",
    "10": "Xác thực thông tin thẻ/tài khoản quá 3 lần",
    "11": "Đã hết hạn chờ thanh toán",
    "12": "Thẻ/Tài khoản bị khóa",
    "13": "Sai mật khẩu OTP",
    "24": "Khách hàng hủy giao dịch",
    "51": "Tài khoản không đủ số dư",
    "65": "Vượt hạn mức giao dịch trong ngày",
    "75": "Ngân hàng đang bảo trì",
    "79": "Nhập sai mật khẩu quá số lần quy định",
    "99": "Lỗi không xác định",
}


# ============================================================
#  MOMO
# ============================================================

MOMO_PARTNER_CODE = os.environ.get("MOMO_PARTNER_CODE", "MOMOBKUN20180529")
MOMO_ACCESS_KEY   = os.environ.get("MOMO_ACCESS_KEY",   "klm05TvNBzhg7h7j")
MOMO_SECRET_KEY   = os.environ.get("MOMO_SECRET_KEY",   "at67qH6mk8w5Y1nAyMoTN1CVo3TpHv4a")
MOMO_ENDPOINT     = os.environ.get("MOMO_ENDPOINT",     "https://test-payment.momo.vn/v2/gateway/api/create")
MOMO_RETURN_URL   = os.environ.get("MOMO_RETURN_URL",   "http://localhost:5000/payment/momo/return")
MOMO_NOTIFY_URL   = os.environ.get("MOMO_NOTIFY_URL",   "http://localhost:5000/payment/momo/notify")


def momo_create_payment(order_id, amount, order_info):
    """
    Tạo request thanh toán MoMo.
    Trả về (pay_url: str | None, message: str)
    """
    request_id   = str(uuid.uuid4())
    order_id_str = f"LUXE{order_id}"
    extra_data   = ""
    request_type = "payWithATM"  # hoặc "captureWallet" cho ví MoMo

    # Chuỗi raw data để ký — thứ tự theo tài liệu MoMo v2
    raw_signature = (
        f"accessKey={MOMO_ACCESS_KEY}"
        f"&amount={int(amount)}"
        f"&extraData={extra_data}"
        f"&ipnUrl={MOMO_NOTIFY_URL}"
        f"&orderId={order_id_str}"
        f"&orderInfo={order_info}"
        f"&partnerCode={MOMO_PARTNER_CODE}"
        f"&redirectUrl={MOMO_RETURN_URL}"
        f"&requestId={request_id}"
        f"&requestType={request_type}"
    )

    signature = hmac.new(
        MOMO_SECRET_KEY.encode("utf-8"),
        raw_signature.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    payload = {
        "partnerCode": MOMO_PARTNER_CODE,
        "accessKey":   MOMO_ACCESS_KEY,
        "requestId":   request_id,
        "amount":      str(int(amount)),
        "orderId":     order_id_str,
        "orderInfo":   order_info,
        "redirectUrl": MOMO_RETURN_URL,
        "ipnUrl":      MOMO_NOTIFY_URL,
        "extraData":   extra_data,
        "requestType": request_type,
        "signature":   signature,
        "lang":        "vi",
    }

    try:
        response = requests.post(
            MOMO_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        result = response.json()

        if result.get("resultCode") == 0:
            return result.get("payUrl"), "OK"
        else:
            return None, result.get("message", "Lỗi từ MoMo")

    except requests.exceptions.Timeout:
        return None, "Kết nối tới MoMo bị timeout"
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"


def momo_verify_return(params):
    """
    Xác thực chữ ký khi MoMo redirect về.
    Trả về (is_valid: bool, result_code: int, order_id: str)
    """
    result_code   = int(params.get("resultCode", -1))
    order_id_str  = params.get("orderId", "")
    received_sig  = params.get("signature", "")

    # Bỏ prefix LUXE để lấy lại order_id gốc
    order_id = order_id_str.replace("LUXE", "")

    raw_signature = (
        f"accessKey={MOMO_ACCESS_KEY}"
        f"&amount={params.get('amount', '')}"
        f"&extraData={params.get('extraData', '')}"
        f"&message={params.get('message', '')}"
        f"&orderId={order_id_str}"
        f"&orderInfo={params.get('orderInfo', '')}"
        f"&orderType={params.get('orderType', '')}"
        f"&partnerCode={MOMO_PARTNER_CODE}"
        f"&payType={params.get('payType', '')}"
        f"&requestId={params.get('requestId', '')}"
        f"&responseTime={params.get('responseTime', '')}"
        f"&resultCode={result_code}"
        f"&transId={params.get('transId', '')}"
    )

    expected_sig = hmac.new(
        MOMO_SECRET_KEY.encode("utf-8"),
        raw_signature.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(expected_sig, received_sig)
    return is_valid, result_code, order_id
