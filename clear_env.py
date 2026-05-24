import os
import subprocess

def clear_env_var(name):
    print(f"Cleaning {name} from Windows Environment Variables...")
    # Clear User level
    subprocess.run(["powershell", "-Command", f"[Environment]::SetEnvironmentVariable('{name}', $null, 'User')"], check=True)
    # Clear Machine level (might require admin, but we'll try)
    try:
        subprocess.run(["powershell", "-Command", f"[Environment]::SetEnvironmentVariable('{name}', $null, 'Machine')"], check=True)
    except:
        print(f"Note: Could not clear {name} from Machine level (needs Admin), but User level should be enough.")

if __name__ == "__main__":
    clear_env_var("GROQ_API_KEY")
    print("\nSUCCESS! Variabel lingkungan Windows sudah dibersihkan.")
    print("Sekarang silakan restart terminal backend kamu agar ia membaca file .env yang baru.")
