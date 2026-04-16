from ollama import chat

while True:
    i = input("Enter prompt ").strip()
    if i == "exit":
        break
    response = chat(model="llama3:8b", messages=[{"role": "user", "content": i}])
    print("AI: ", response.message.content)
