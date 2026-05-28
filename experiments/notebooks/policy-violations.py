import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium", layout_file="layouts/rag-poc.grid.json")

with app.setup:
    from openai import OpenAI
    import marimo as mo

    client = OpenAI()


@app.function
def query_open_ai(case_detail: str):
    response = client.responses.create(
    model="gpt-4.1",
    input=f"""
    I have the case details of a victim here. 

    {case_detail}

    Can you tell me which of Meta's policy can be applied to request takedown of this content? 

    Keep your answer succint. Do not recommend actions I should take. Just tell me which clauses by quoting verbatim from the policy document. Tell me which category of harm it would fall under. Be thorough in your search. Its more important to include relevant clauses than to miss any relevant clause. Make sure the category of harms are in decreasing order of relevance. The most pertinent clause should come first. by pertinent we mean a policy that has implications of content takedown. Because the most serious action that the platform can take is content takedown. So if there's a policy that will lead to this content's takedown, that should come first. 

    The case details contain description by the suvivor. It might not be how meta sees the incident so we careful about presenting clauses that Meta is more likely to believe and ackowledge.

    Expected Response Format :
    For each matching category of harm 
        Category of harm
        Verbatim snippet of the policy
    Ensure that the response is formatted as markdown, with appropriate heading tags.


    Also at the end, tell me your reasoning for choosing the order of harms
    """,
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["vs_69df362c6bdc81918145de014e60f7de"]
    }]
    )

    return response.output_text


@app.cell
def _():
    text_case_details = mo.ui.text_area(placeholder="Enter Case Details")
    return (text_case_details,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Case Details
    """)
    return


@app.cell
def _():
    run_button = mo.ui.run_button(label="Find Clauses")
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
