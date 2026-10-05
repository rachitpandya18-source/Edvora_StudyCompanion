from app.services.llm_service import generate_response


response = generate_response(
    "Explain the piezoelectric effect in 3 simple sentences."
)

print("\nGemini Response:")
print(response)