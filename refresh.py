# ======================================================
# XEBERLERI BIRGE YENILEME SKRIPTI (APA.AZ + REPORT.AZ)
# ======================================================
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
PYTHON_EXE = sys.executable

def main():
    print("=" * 60)
    print("XƏBƏRLƏRİN YENİLƏNMƏSİ BAŞLADI (APA.AZ + REPORT.AZ)")
    print("=" * 60)

    # 1. APA.AZ
    print("\n>>> [1/2] APA.AZ yenilənir...")
    p1 = subprocess.run([PYTHON_EXE, str(ROOT_DIR / "apa_az" / "main.py")])
    if p1.returncode != 0:
        print("⚠️ APA.az skriptində xəta baş verdi.")

    # 2. REPORT.AZ
    print("\n>>> [2/2] REPORT.AZ yenilənir...")
    p2 = subprocess.run([PYTHON_EXE, str(ROOT_DIR / "report_az" / "fix_and_refresh_az.py")])
    if p2.returncode != 0:
        print("⚠️ Report.az skriptində xəta baş verdi.")

    print("\n" + "=" * 60)
    print("✅ BÜTÜN YENİLƏNMƏ PROSESİ BİTDİ!")
    print("=" * 60)

if __name__ == "__main__":
    main()

