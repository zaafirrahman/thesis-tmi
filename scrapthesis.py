import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# Setup
options = webdriver.ChromeOptions()
# options.add_argument('--headless') # Buka ini kalau mau running di background
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

all_data = []
counter = 1
wait = WebDriverWait(driver, 15) # Maksimal nunggu 15 detik

try:
    url = "https://digilib.itb.ac.id/prodi/index/2820"
    driver.get(url)
    
    while True:
        print(f"Scraping halaman... (Data terkumpul: {len(all_data)})")
        
        # 1. Tunggu container judul muncul
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'col-lg-11')]")))
        
        # Ambil semua link judul di page ini
        thesis_links = driver.find_elements(By.XPATH, "//div[contains(@class, 'col-lg-11')]//a[contains(@href, 'view_data')]")
        
        for link in thesis_links:
            # .text otomatis nge-join span huruf yang pecah-pecah
            title = link.text.replace("Tesis", "").strip()
            if title:
                all_data.append({"No": counter, "Judul Tesis": title})
                counter += 1

        # 2. Logic klik tombol "Next"
        try:
            # Tunggu tombol Next muncul dan bisa diklik
            next_xpath = "//a[contains(@aria-label, 'Next') or contains(text(), 'Next') or contains(text(), '»')]"
            
            # Cek apakah tombol Next ada di DOM
            next_buttons = driver.find_elements(By.XPATH, next_xpath)
            
            if len(next_buttons) > 0:
                next_button = next_buttons[0]
                
                # Scroll biar kelihatan (mencegah ElementClickInterceptedError)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(1) # Jeda dikit biar scroll-nya smooth
                
                next_button.click()
                
                # Tunggu URL berubah atau page reload (stale element check)
                time.sleep(2) 
            else:
                print("Tombol Next tidak ditemukan. Selesai.")
                break
                
        except Exception as e:
            print(f"Berhenti: Mungkin sudah halaman terakhir atau ada error: {e}")
            break

    # Export ke CSV
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv("list_judul_tesis_tmi_itb.csv", index=False)
        print(f"\nSelesai! Total {len(all_data)} judul tersimpan di 'semua_judul_tesis_tmi_itb.csv'")
    else:
        print("Yah, nggak ada data yang ke-grab.")

finally:
    driver.quit()