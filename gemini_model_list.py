from google import genai

client = genai.Client(api_key="AIzaSyBWFk3cP1iSib8p_CA-2u4HmJS6XB0cleM")

for m in client.models.list():
    print(m.name)