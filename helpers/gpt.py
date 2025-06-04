import openai

def summarize_post_and_generate_ideas(title, body):
    prompt = f"""Reddit post:
Title: {title}
Body: {body}

Summarize the post in 1 sentence. Then say if this could inspire a unique, new t-shirt idea that has not yet been saturated. If yes, give the exact phrase or design idea.

Respond in JSON like this:
{{"summary": "...", "viable_idea": true/false, "idea": "..."}}"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return eval(response.choices[0].message["content"])  # If the response is JSON
