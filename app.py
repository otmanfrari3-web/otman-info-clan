import httpx
from flask import Flask, request, jsonify
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import stevedata_pb2
import steveencode_pb2

app = Flask(__name__)

# ===================== CONFIG =====================

FREEFIRE_VERSION = "OB53"

KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])

# JWT API (النفسه بس الرد هيكون مختلف)
JWT_API = (
    "https://access-to-jw-tt.vercel.app/token?uid=4889645792&password=JAGWAR-KING-IS-BACK_FF_Zo77sQh3"
)

# In-memory cache (Vercel friendly)
JWT_CACHE = {
    "token": None,
    "time": 0
}

TOKEN_TTL = 300  # seconds

# ===================== HELPERS =====================

def get_jwt_token():
    now = datetime.utcnow().timestamp()

    if JWT_CACHE["token"] and (now - JWT_CACHE["time"] < TOKEN_TTL):
        return JWT_CACHE["token"]

    try:
        r = httpx.get(JWT_API, timeout=10)
        r.raise_for_status()
        data = r.json()

        # التعديل هنا: التعامل مع الرد الجديد
        # الرد الجديد يحتوي على "token" مباشرةً
        token = data.get("token")
        
        # يمكنك أيضاً تخزين معلومات إضافية إذا احتجتها
        region = data.get("region")
        status = data.get("status")
        team = data.get("team")
        uid = data.get("uid")
        token_access = data.get("token_access")
        
        if not token:
            print("Token not found in response. Response structure:", data.keys())
            return None

        # تخزين التوكن فقط (أو يمكنك تخزين معلومات إضافية)
        JWT_CACHE["token"] = token
        JWT_CACHE["time"] = now
        
        # طباعة معلومات للdebug (اختياري)
        print(f"Token obtained successfully for UID: {uid}")
        print(f"Region: {region}, Status: {status}, Team: {team}")
        
        return token

    except Exception as e:
        print("JWT fetch error:", e)
        return None


def get_full_jwt_data():
    """دالة إضافية لاسترجاع كل بيانات JWT API"""
    try:
        r = httpx.get(JWT_API, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        return {
            "region": data.get("region"),
            "status": data.get("status"),
            "team": data.get("team"),
            "token": data.get("token"),
            "token_access": data.get("token_access"),
            "uid": data.get("uid")
        }
    except Exception as e:
        print("Failed to fetch JWT data:", e)
        return None


def ts(value):
    if not value:
        return None
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")

# ===================== ROUTE =====================

@app.route("/get_clan_info", methods=["GET"])
def get_clan_info():
    clan_id = request.args.get("clan_id")
    if not clan_id:
        return jsonify({"error": "clan_id is required"}), 400

    jwt_token = get_jwt_token()
    if not jwt_token:
        return jsonify({"error": "Failed to fetch JWT token"}), 500

    # -------- protobuf encode --------
    my_data = steveencode_pb2.MyData()
    my_data.field1 = int(clan_id)
    my_data.field2 = 1

    raw = my_data.SerializeToString()
    encrypted = AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(raw, 16))

    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": FREEFIRE_VERSION,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; Android 11)",
        "Host": "clientbp.ggblueshark.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }

    try:
        r = httpx.post(
            "https://clientbp.ggpolarbear.com/GetClanInfoByClanID",
            headers=headers,
            content=encrypted,
            timeout=httpx.Timeout(15.0, connect=5.0)
        )
    except Exception as e:
        return jsonify({"error": "Upstream request error", "detail": str(e)}), 500

    if r.status_code != 200 or not r.content:
        return jsonify({
            "error": "Upstream request failed",
            "status": r.status_code
        }), r.status_code

    # -------- protobuf decode (FULL DATA) --------
    try:
        resp = stevedata_pb2.response()
        resp.ParseFromString(r.content)

        return jsonify({
            "id": resp.id,
            "clan_name": resp.special_code,

            "timestamp1": ts(resp.timestamp1),
            "timestamp2": ts(resp.timestamp2),
            "last_active": ts(resp.last_active),

            "value_a": resp.value_a,
            "status_code": resp.status_code,
            "sub_type": resp.sub_type,
            "version": resp.version,
            "level": resp.level,
            "flags": resp.flags,
            "welcome_message": resp.welcome_message,
            "region": resp.region,

            "json_metadata": resp.json_metadata,
            "big_numbers": resp.big_numbers,
            "balance": resp.balance,
            "score": resp.score,
            "upgrades": resp.upgrades,
            "achievements": resp.achievements,
            "total_playtime": resp.total_playtime,
            "energy": resp.energy,
            "rank": resp.rank,
            "xp": resp.xp,
            "error_code": resp.error_code,

            "guild_details": {
                "clan_id": resp.guild_details.clan_id,
                "region": resp.guild_details.region,
                "members_online": resp.guild_details.members_online,
                "total_members": resp.guild_details.total_members,
                "regional": resp.guild_details.regional,
                "reward_time": resp.guild_details.reward_time,
                "expire_time": resp.guild_details.expire_time
            }
        })

    except Exception as e:
        return jsonify({
            "error": "Protobuf parse error",
            "detail": str(e)
        }), 500


# ===================== ENDPOINT إضافي لعرض معلومات JWT =====================

@app.route("/get_jwt_info", methods=["GET"])
def get_jwt_info():
    """Endpoint لعرض معلومات JWT API كاملة"""
    jwt_data = get_full_jwt_data()
    if not jwt_data:
        return jsonify({"error": "Failed to fetch JWT data"}), 500
    
    return jsonify(jwt_data)


@app.route("/get_clan_info_with_jwt_details", methods=["GET"])
def get_clan_info_with_jwt_details():
    """نفس get_clan_info لكن يعرض معلومات JWT المستخدمة"""
    clan_id = request.args.get("clan_id")
    if not clan_id:
        return jsonify({"error": "clan_id is required"}), 400
    
    # جلب بيانات JWT كاملة
    jwt_data = get_full_jwt_data()
    if not jwt_data or not jwt_data.get("token"):
        return jsonify({"error": "Failed to fetch JWT data"}), 500
    
    jwt_token = jwt_data["token"]
    
    # بقية الكود نفس اللي فوق...
    my_data = steveencode_pb2.MyData()
    my_data.field1 = int(clan_id)
    my_data.field2 = 1

    raw = my_data.SerializeToString()
    encrypted = AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(raw, 16))

    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": FREEFIRE_VERSION,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; Android 11)",
        "Host": "clientbp.ggblueshark.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }

    try:
        r = httpx.post(
            "https://clientbp.ggpolarbear.com/GetClanInfoByClanID",
            headers=headers,
            content=encrypted,
            timeout=httpx.Timeout(15.0, connect=5.0)
        )
    except Exception as e:
        return jsonify({"error": "Upstream request error", "detail": str(e)}), 500

    if r.status_code != 200 or not r.content:
        return jsonify({
            "error": "Upstream request failed",
            "status": r.status_code
        }), r.status_code

    try:
        resp = stevedata_pb2.response()
        resp.ParseFromString(r.content)

        return jsonify({
            "jwt_used": {
                "region": jwt_data.get("region"),
                "status": jwt_data.get("status"),
                "team": jwt_data.get("team"),
                "uid": jwt_data.get("uid"),
                "token_access": jwt_data.get("token_access")
            },
            "clan_info": {
                "id": resp.id,
                "clan_name": resp.special_code,
                "timestamp1": ts(resp.timestamp1),
                "timestamp2": ts(resp.timestamp2),
                "last_active": ts(resp.last_active),
                "level": resp.level,
                "rank": resp.rank,
                "region": resp.region,
                "guild_details": {
                    "clan_id": resp.guild_details.clan_id,
                    "members_online": resp.guild_details.members_online,
                    "total_members": resp.guild_details.total_members
                }
            }
        })

    except Exception as e:
        return jsonify({
            "error": "Protobuf parse error",
            "detail": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)