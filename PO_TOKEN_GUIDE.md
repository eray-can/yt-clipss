# YouTube po_token Nasıl Alınır?

## Adımlar

### 1. YouTube'u Tarayıcıda Aç
- https://www.youtube.com adresine git ve giriş yap

### 2. Developer Console'u Aç
- Chrome/Firefox: `F12` tuşuna bas
- Console sekmesine git

### 3. Bu Kodu Çalıştır

```javascript
console.log('PO_TOKEN:', window.ytcfg?.data_?.PO_TOKEN);
console.log('VISITOR_DATA:', window.ytcfg?.data_?.VISITOR_DATA);
```

### 4. Değerleri Kopyala
Console'da çıkan değerleri kopyala.

## Dokploy'da Kullanım

Dokploy'da projenizin **Environment Variables** bölümüne ekleyin:

```
YOUTUBE_PO_TOKEN=<po_token_değeri>
YOUTUBE_VISITOR_DATA=<visitor_data_değeri>
```

Bu değerler olmadan YouTube bot koruması devreye girer.
