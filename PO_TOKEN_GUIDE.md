# YouTube po_token Nasıl Alınır?

## Adımlar

### 1. YouTube'u Tarayıcıda Aç
- https://www.youtube.com adresine git ve giriş yap

### 2. Developer Console'u Aç
- Chrome/Firefox: `F12` tuşuna bas
- Console sekmesine git

### 3. Bu Kodu Çalıştır

**Yöntem 1 - ytcfg'den:**
```javascript
console.log('PO_TOKEN:', window.ytcfg?.data_?.PO_TOKEN);
console.log('VISITOR_DATA:', window.ytcfg?.data_?.VISITOR_DATA);
```

**Yöntem 2 - ytInitialPlayerResponse'dan (daha güvenilir):**
```javascript
// Herhangi bir video sayfasına gidin (örn: youtube.com/watch?v=...)
console.log('PO_TOKEN:', window.ytInitialPlayerResponse?.serviceTrackingParams?.find(x=>x.service==='CSI')?.params?.find(x=>x.key==='po_token')?.value);
console.log('VISITOR_DATA:', window.ytInitialData?.responseContext?.visitorData);
```

**Yöntem 3 - Network'ten:**
1. Developer Tools → **Network** sekmesi
2. Bir video izleyin
3. `player` veya `youtubei/v1/player` isteğini bulun
4. Request Headers'da `X-Goog-Visitor-Id` ve response'da `serviceTrackingParams` kontrol edin

### 4. Değerleri Kopyala
Console'da çıkan değerleri kopyala.

## Dokploy'da Kullanım

Dokploy'da projenizin **Environment Variables** bölümüne ekleyin:

```
YOUTUBE_PO_TOKEN=<po_token_değeri>
YOUTUBE_VISITOR_DATA=<visitor_data_değeri>
```

Bu değerler olmadan YouTube bot koruması devreye girer.
