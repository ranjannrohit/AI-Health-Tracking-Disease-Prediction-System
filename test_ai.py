from groq import Groq

client = Groq(api_key="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")

chat_completion = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "What is diabetes?"}
    ],
    model="llama-3.3-70b-versatile"
)

print(chat_completion.choices[0].message.content)
