import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    from openai import OpenAI
    import marimo as mo

    client = OpenAI()


@app.function
def query_open_ai(question: str):
    response = client.responses.create(
    model="gpt-4.1",
    input=question,
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["vs_69df362c6bdc81918145de014e60f7de"]
    }]
    )

    return response.output_text


@app.cell
def _():
    text_case_details = mo.ui.text_area(placeholder="Aur bataiye...")
    return (text_case_details,)


@app.cell
def _():
    run_button = mo.ui.run_button(label="Ask LLM")
    return (run_button,)


@app.cell
def _(run_button, text_case_details):
    mo.stop(not run_button.value)
    response = query_open_ai(text_case_details.value)
    return (response,)


@app.cell
def _(run_button, text_case_details):
    mo.vstack(
        [
            text_case_details,
            run_button
        ]
    )
    return


@app.cell
def _(response):
    mo.md(response)
    return


if __name__ == "__main__":
    app.run()
