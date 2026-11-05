# ======================================================
# XEBERLERI BIRGE YENILEME SKRIPTI (APA.AZ + REPORT.AZ + TREND.AZ)
# ======================================================
import subprocess
import sys
from pathlib import Path

# Windows terminalında Azərbaycan şriftləri və emojilər üçün UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.resolve()
PYTHON_EXE = sys.executable

SCRIPTS = [
    ("APA.AZ", ROOT_DIR / "apa_az" / "main.py"),
    ("REPORT.AZ", ROOT_DIR / "report_az" / "fix_and_refresh_az.py"),
    ("TREND.AZ", ROOT_DIR / "trend_az" / "main.py"),
]

def main():
    print("=" * 60)
    print("XƏBƏRLƏRİN YENİLƏNMƏSİ BAŞLADI (APA.AZ + REPORT.AZ + TREND.AZ)")
    print("=" * 60)

    failed = []

    for idx, (name, path) in enumerate(SCRIPTS, start=1):
        print(f"\n>>> [{idx}/{len(SCRIPTS)}] {name} yenilənir...")
        
        if not path.exists():
            print(f"❌ Xəta: {path} faylı tapılmadı!")
            failed.append(name)
            continue

        result = subprocess.run([PYTHON_EXE, str(path)], cwd=ROOT_DIR)
        
        if result.returncode != 0:
            print(f"⚠️ {name} skriptində xəta baş verdi (kod: {result.returncode})!")
            failed.append(name)
        else:
            print(f"✔️ {name} uğurla tamamlandı.")

    print("\n" + "=" * 60)
    if failed:
        print(f"❌ Yenilənmə başa çatdı, lakin xəta baş verən saytlar var: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("✅ BÜTÜN SAYTLAR UĞURLA YENİLƏNDİ!")
        print("=" * 60)

if __name__ == "__main__":
    main()
