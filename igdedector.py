import requests
import json
import time
from datetime import datetime, timezone

sessionid = input("Instagram sessionid çerezini girin: ")
shortcode = input("Instagram gönderi kısa kodunu girin (örn: DD7srGYoj2F): ")

print("\nSeçenekler:")
print("1- Tam Arama (Tüm yorumları kaydeder)")
print("2- Kullanıcı Adı ile Arama (Sadece belirli bir kişinin yorumlarını gösterir)")
secim = input("Seçiminizi yapın (1 veya 2): ")

if secim == "2":
    target_username = input("Hangi kullanıcının yorumlarını bulmak istiyorsunuz?: ")
else:
    target_username = None

# API URL (GraphQL endpoint)
base_url = "https://www.instagram.com/graphql/query/"
query_hash = "97b41c52301f77ce508f55e66d17620e"
first = 60  # Küçük parçalarda yorum çekiyoruz
after = None  # Yorum sayfası ilerleme token'i

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"https://www.instagram.com/p/{shortcode}/"
}
cookies = {"sessionid": sessionid}

count_total = 0  # Toplam çekilen yorum sayısı
count_saved = 0  # Kaydedilen yorum sayısı
TIMEOUT = 30  # Zaman aşımı süresi 30 saniye
MAX_RETRIES = 5  # Maksimum tekrar deneme sayısı
WAIT_TIME = 10  # İlk hata sonrası bekleme süresi
dynamic_wait_time = 30  # API limitine takılmamak için bekleme süresi

def get_total_comments():
    url = f"https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables=%7B%22shortcode%22%3A%22{shortcode}%22%2C%22first%22%3A1%7D"
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            total_comments = data["data"]["shortcode_media"]["edge_media_to_parent_comment"]["count"]
            print(f"📢 Hedef gönderide toplam {total_comments} yorum var.")
            return total_comments
        else:
            print(f"⚠ Yorum sayısı alınamadı. HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"⚠ Bağlantı hatası: {e}")
        return None

total_comments = get_total_comments()

with open("yorumlar.txt", "w", encoding="utf-8") as file:
    while True:
        variables = {"shortcode": shortcode, "first": first}
        if after:
            variables["after"] = after

        url = f"{base_url}?query_hash={query_hash}&variables={json.dumps(variables)}"

        # Bağlantı hatalarında otomatik tekrar deneme
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, headers=headers, cookies=cookies, timeout=TIMEOUT)
                if response.status_code == 200:
                    break
                else:
                    print(f"⚠ HTTP Hata {response.status_code} - Yeniden deneniyor... ({attempt}/{MAX_RETRIES})")

            except requests.exceptions.RequestException as e:
                print(f"⚠ Bağlantı hatası: {e} - {attempt}/{MAX_RETRIES} deneme, {WAIT_TIME} saniye bekleniyor...")
                time.sleep(WAIT_TIME)
                WAIT_TIME *= 2

            if attempt == MAX_RETRIES:
                print("❌ Bağlantı başarısız. Tüm denemeler tükendi.")
                exit()

        data = response.json()
        comments = data["data"]["shortcode_media"]["edge_media_to_parent_comment"]["edges"]
        page_info = data["data"]["shortcode_media"]["edge_media_to_parent_comment"]["page_info"]
        after = page_info["end_cursor"] if page_info["has_next_page"] else None

        count_total += len(comments)
        print(f"✅ {count_total} yorum çekildi, {count_saved} yorum kaydedildi...")

        for comment in comments:
            username = comment["node"]["owner"]["username"]
            text = comment["node"]["text"]
            timestamp = comment["node"]["created_at"]
            comment_time = datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

            if target_username:
                if username == target_username:
                    file.write(f"{comment_time} - {username}: {text}\n")
                    file.flush()
                    print(f"🔍 {comment_time} - {username}: {text}")  # **Sadece hedef kullanıcı ekrana yazılacak**
                    count_saved += 1
            else:
                file.write(f"{comment_time} - {username}: {text}\n")
                file.flush()
                count_saved += 1

        if total_comments and count_total >= total_comments:
            print("🚀 Tüm yorumlar başarıyla çekildi!")
            break
        elif not after:
            print(f"⚠ Tüm yorumları alamadık! Çekilen yorum: {count_total} / {total_comments}")
            break

        if count_total >= 500 and count_total % 500 < first:
            print(f"⏳ {count_total} yorum çekildi, {dynamic_wait_time} saniye bekleniyor...")
            time.sleep(dynamic_wait_time)
            dynamic_wait_time += 10

        if not after:
            print("🚀 Daha fazla yorum yok. İşlem tamamlandı.")
            break

        if count_total < 1000:
            time.sleep(2)
        else:
            time.sleep(5)

print(f"🎉 Toplam {count_total} yorum çekildi, {count_saved} yorum kaydedildi: yorumlar.txt")
