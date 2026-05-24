import sys, os
sys.path.append(os.path.abspath("e:/COOLYEAH/PA/gempa/backend"))

# Check env BEFORE loading dotenv
key_before = os.environ.get("GROQ_API_KEY", "")
print(f"Key from OS env (before dotenv): {key_before[:15]}...{key_before[-4:] if key_before else ''}")

from dotenv import load_dotenv
load_dotenv()

key_after = os.environ.get("GROQ_API_KEY", "")
print(f"Key after dotenv: {key_after[:15]}...{key_after[-4:] if key_after else ''}")

# Check what Groq client actually uses
from groq import Groq
client = Groq(api_key=key_after)
print(f"\nGroq client using key: {client.api_key[:15]}...{client.api_key[-4:]}")
