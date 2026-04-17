from ollama import chat

if __name__ == "__main__":
    history = []
    while True:

        user_input = input("Enter prompt: ").strip()
        if user_input == "exit":
            break

        message = {
            "role": "user",
            "content": user_input,
        }

        history.append(message)
        response = chat(model="llama3:8b", messages=history)
        ai_response_content = response.message.content
        ai_message = {"role": "assistant", "content": ai_response_content}
        print("AI: ", ai_response_content)
        history.append(ai_message)
