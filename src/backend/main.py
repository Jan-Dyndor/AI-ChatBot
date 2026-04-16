from ollama import chat


if __name__ == "__main__":
    while True:
        i = input("Enter prompt ").strip()
        if i == "exit":
            break
        response = chat(model="llama3:8b", messages=[{"role": "user", "content": i}])
        print("AI: ", response.message.content)
