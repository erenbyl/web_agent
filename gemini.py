import os
import time
import nbformat
import google.generativeai as genai
import google.api_core.exceptions

# Gemini'yi başlat
genai.configure(api_key="")  # Buraya kendi API key'ini koy

model = genai.GenerativeModel("gemini-1.5-flash")

def generate_feedback(code: str, markdown_context: str = "") -> str:
    """Kodun doğruluğunu kontrol et ve kısa geri bildirim ver (Gemini ile)."""
    
    if code.strip():
        prompt = f"""
Aşağıda bir Python ödev sorusuna öğrencinin verdiği kod cevabı var.
Sadece kodu kontrol et. Kod doğruysa "Evet, doğru." yaz.
Kodda hata varsa, sadece hatalı kısmı belirt ve doğru halini göster:
"Kodun şu kısmı hatalı: ... Doğrusu şu şekilde olmalı: ..."

Kod:
```python
{code}
```"""
    else:
        prompt = f"""
Aşağıda bir Python ödev sorusu var. Bu soruya öğrenci henüz bir çözüm yazmamış.
Bu nedenle, soruya uygun şekilde örnek bir Python çözümü ver ve çözümü kısa ve öz olarak açıkla.

Soru:
{markdown_context}
"""

    retry_count = 3  # Maksimum 3 deneme hakkı
    for attempt in range(retry_count):
        try:
            response = model.generate_content(prompt)
            time.sleep(1)  # Rate limit’e takılmamak için bekle
            return response.text.strip()
        except google.api_core.exceptions.ResourceExhausted as e:
            print(f"⚠️ API kotası aşıldı, {attempt + 1}. deneme ({10 * (attempt + 1)} sn bekleme)...")
            time.sleep(10 * (attempt + 1))  # Artan bekleme süresi (exponential backoff)
        except Exception as e:
            print(f"❌ Beklenmeyen bir hata oluştu: {e}")
            break  # Diğer hatalar için döngüyü kes

    return "[API kotası aşıldığı için geri bildirim üretilemedi.]"

def read_notebook(path: str):
    """Notebook dosyasını okuyup kod ve markdown hücrelerini döndürür."""
    with open(path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    code_cells = [cell['source'] for cell in nb.cells if cell['cell_type'] == 'code']
    markdown_cells = [cell['source'] for cell in nb.cells if cell['cell_type'] == 'markdown']

    return code_cells, markdown_cells

def process_notebook(notebook_path: str, feedback_dir: str):
    print(f"\n\n📘 Dosya: {notebook_path}")
    print("=" * 80)

    start_time = time.time()  # İşlem süresi başlangıcı

    code_blocks, markdown_blocks = read_notebook(notebook_path)

    # Dosya adından e-posta bilgisini çıkar (hafta zaten klasör adı)
    basename = os.path.basename(notebook_path)
    email = basename.replace(".ipynb", "")

    feedback_filename = os.path.join(feedback_dir, f"{email}_feedback.txt")

    with open(feedback_filename, "w", encoding="utf-8") as feedback_file:
        code_index = 0
        for i, markdown in enumerate(markdown_blocks, 1):
            print(f"\n=== Markdown Hücresi {i} ===")
            print(markdown)
            print("\n" + "=" * 60)

            if any(word in markdown.lower() for word in ["soru", "problemi", "ödev"]):
                if code_index < len(code_blocks):
                    kod = code_blocks[code_index].strip()
                    print(f"\n=== Kod Hücresi {code_index + 1} ===")
                    print(kod if kod else "[Boş Kod Hücresi]")

                    print("\n--- Geri Bildirim ---")
                    feedback = generate_feedback(kod, markdown)
                    print(feedback)
                    print("\n" + "=" * 60)

                    feedback_file.write(f"Soru {i} - Geri Bildirim:\n{feedback}\n\n")
                    code_index += 1

    end_time = time.time()
    duration = end_time - start_time
    print(f"\n⏱️ Bu dosya {duration:.2f} saniyede işlendi. Geri bildirimler şuraya kaydedildi: {feedback_filename}")
    return duration

def main():
    odevler_klasoru = "odevler"  # Ana odevler klasörü
    if not os.path.exists(odevler_klasoru):
        print(f"📂 '{odevler_klasoru}' klasörü bulunamadı.")
        return

    toplam_sure = 0.0
    dosya_sureleri = {}

    # "odevler" içindeki her hafta klasörü
    hafta_klasorleri = [d for d in os.listdir(odevler_klasoru)
                        if os.path.isdir(os.path.join(odevler_klasoru, d))]

    if not hafta_klasorleri:
        print(f"📂 '{odevler_klasoru}' klasörü içinde hafta klasörü bulunamadı.")
        return

    for hafta_klasoru in hafta_klasorleri:
        hafta_yolu = os.path.join(odevler_klasoru, hafta_klasoru)
        ipynb_dosyalar = [f for f in os.listdir(hafta_yolu) if f.endswith(".ipynb")]
        if not ipynb_dosyalar:
            print(f"📂 '{hafta_klasoru}' klasöründe .ipynb dosyası bulunamadı.")
            continue

        # Feedback için hafta bazlı klasör oluştur
        feedback_hafta_klasoru = os.path.join("feedback", f"{hafta_klasoru}_feedback")
        os.makedirs(feedback_hafta_klasoru, exist_ok=True)

        print(f"\n🔍 '{hafta_klasoru}' klasöründeki ödevler kontrol ediliyor...")

        for dosya in ipynb_dosyalar:
            tam_yol = os.path.join(hafta_yolu, dosya)
            sure = process_notebook(tam_yol, feedback_hafta_klasoru)
            dosya_sureleri[f"{hafta_klasoru}/{dosya}"] = sure
            toplam_sure += sure

    print("\n🕒 Dosya İşlem Süreleri:")
    print("-" * 30)
    for dosya, sure in dosya_sureleri.items():
        print(f"{dosya}: {sure:.2f} saniye")

    print(f"\n✅ Tüm dosyaların kontrolü tamamlandı. Toplam süre: {toplam_sure:.2f} saniye.")

if __name__ == "__main__":
    main()
