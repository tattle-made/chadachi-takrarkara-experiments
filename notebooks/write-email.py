import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    # /// script
    # [tool.marimo.opengraph]
    # title = "Email Generation"
    # description = "Provide Case details -> Generate Email Draft -> Record your Feedback"
    # ///
    return


@app.cell
def _():
    from openai import OpenAI
    import marimo as mo

    client = OpenAI()
    return client, mo


@app.cell
def _(client):
    def query_open_ai(case_detail: str):
        response = client.responses.create(
        model="gpt-4.1",
        input=f"""

    I am a trust and safety expert whose job is to help support victims of cybercrimes.

    Your task is to assist me in drafting emails to be sent to social media platforms based on the unique nuances of victim's case.

    I have the case details of a victim here. 

        {case_detail}

    ## Email Structure 
    The structure of the generated email should be like this
    (greetings from our team)

    (summary of case details highlighting the impact on victim's wellbeing)

    (elaborate all instances of abuse)

    (insert a note if it is a repeat case)    

    (insert community guideline violations)
    	Mention all Meta policy that can be applied to request takedown of the content.
    	Cite verbatim snippet from the policy documents

    (closing remark summarizing our ask)

    # General instructions on the tone of the email
    Keep your answer succint. Be thorough in your search. Its more important to include all relevant clauses than to miss any relevant clause. Make sure the category of harms are in decreasing order of relevance. The most pertinent clause should come first. by pertinent we mean a policy that has implications of content takedown. Because the most serious action that the platform can take is content takedown. So if there's a policy that will lead to this content's takedown, that should come first. 

    Please be aware that I will add relevant evidence and attachments to this email, so you don't need to provide too much information about the details of the case. For instance its ok to mention that a nude image of the victim was shared online but you don't have to include detailed information of where the video was taken or what the victim was doing in the video.

    Please also note that in no case you should include name of any of the people mentioned in the case detail

    # Example emails
    ## Account Impersonation
    Greetings from Rati Foundation. We are one of the Meta Safety Partners for India.

    We are reporting a fake Facebook account that is impersonating a 32-year-old man by misusing his name and personal photographs, including setting his images as the profile and cover picture.

    He has been making new accounts even after reporting the previous ones. Earlier, the account was reported for Authentic Identity Representation. For reference -  (add reference number here)

    Context - The account is believed to be operated by the ex-partner of the victim’s wife, with whom she ended a relationship approximately two years ago. The perpetrator has recently begun uploading old, intimate images of himself and the victim’s wife—taken during their past relationship—without her or the victim's consent, using the impersonating profile of the victim.
    In addition, the perpetrator has reportedly been sharing these private images and sending unsolicited, harassing messages to the victim’s friends and contacts. These actions have caused severe emotional distress to the victim and have significantly disrupted his personal and social life.

    We urgently request that appropriate action be taken to remove the offending account, and to help protect the victim’s privacy, reputation, and well-being.

    This goes against Meta's community guidelines which states:
    1. Authentic identity representation
    We do not allow the use of our services and will restrict or disable Facebook, Instagram and Threads accounts or other Facebook entities (such as Pages or groups) that: 
    Impersonate another person or entity by:
    - Using their image(s), name or likeness with the aim of deceiving others
    - Speaking in the voice of another person or entity for whom the user is not authorised to do so (e.g. by creating a Page or profile)
    Engage in identity misrepresentation to mislead or deceive others, evade enforcement or violate our Community Standards. We consider a number of factors when assessing misleading identity misrepresentation, such as:
    Repeated or significant changes to identity details, such as name or age

    2. Privacy Violations and Image Privacy Rights Policy
    “We remove content that shares images of private individuals without their consent, particularly when such content could lead to harassment or harm.”

    In support of our request, we have attached the following documentation:
    1. Screenshot of the account and the chat. 

    We respectfully and urgently request the immediate removal of this account  from Facebook.

    ## Cyberbullying
    Greetings from RATI Foundation. 
    We have received a report of an Instagram account that is engaging in persistent harassment of a minor 17-year-old girl. 

    The girl was in an abusive relationship with the perpetrator 

    .A police complaint has also been filed to this end. Despite the police complaint, she continues to be harassed persistently. A copy of the FIR has been attached below.

    In the account mentioned above, the perpetrator has posted photos of the minor victim in a collage with photos of other unknown men.  These posts are accompanied by captions suggesting a romantic and/or sexual relationship between the victim and the men displayed. Some of the victim's photos have been taken from her Instagram non-consensually.  Owing to the legal case and these accounts, she is also being shamed in the community.  

    The actions of this account violate Meta’s Terms of Use, which state that:
    "You can't do anything unlawful, misleading, or fraudulent or for an illegal or unauthorized purpose."
    "You can't post someone else’s private or confidential information without permission or do anything that violates someone else's rights, including intellectual property rights "
    "All private minors, are protected from: Claims about romantic involvement, sexual orientation or gender identity."
    It violates Meta Community Guidelines stating that
     "Only share photos and videos that you've taken or have the right to share. As always, you own the content that you post on Instagram. Remember to post authentic content, and don't post anything you've copied or collected from the Internet that you don't have the right to post (...) Further, Meta provides heightened protections for private individuals, particularly minors, by removing content intended to degrade or shame, such as claims about a person’s sexual activity, recognizing the severe emotional impact that bullying and harassment can have on those under the age of 18.”
    Accordingly Meta's Community Standards on 'Authentic Identity and Representation' state that: 
    "We do not allow the use of our services and will restrict or disable Facebook, Instagram and Threads accounts or other Facebook entities (such as Pages or groups) that:
    Belong to underage children
    Impersonate another person or entity by:
    Using their image(s), name or likeness with the aim of deceiving others.”

    The continued existence of the account is a source of immense emotional and social distress for the victim. We hope this is adequate information for you to take appropriate action at the earliest. In case of any further questions, please reach out to us.


        """,
        tools=[{
            "type": "file_search",
            "vector_store_ids": ["vs_69df362c6bdc81918145de014e60f7de"]
        }]
        )

        return response.output_text

    return (query_open_ai,)


@app.cell
def _(mo):
    text_case_details = mo.ui.text_area(placeholder="Enter Case Details")
    return (text_case_details,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Case Details

    This app is used to generate emails from case details.

    To use the app, write details of the case and click "Generate Email". This app then finds out which platform policies are violated and creates an email that can be sent to the platform.
    """)
    return


@app.cell
def _(mo):
    run_button = mo.ui.run_button(label="Generate Email")
    return (run_button,)


@app.cell
def _(mo, query_open_ai, run_button, text_case_details):
    mo.stop(not run_button.value)
    response = query_open_ai(text_case_details.value)
    return (response,)


@app.cell
def _(mo, run_button, text_case_details):
    mo.vstack(
        [
            text_case_details,
            run_button
        ]
    )
    return


@app.cell
def _():
    import anywidget
    import traitlets
    import json

    class TextAnnotatorWidget(anywidget.AnyWidget):
        _esm = """
        import { marked } from "https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js";

        function render({ model, el }) {
          el.style.fontFamily = "sans-serif";
          el.style.maxWidth = "860px";
          el.style.margin = "0 auto";

          // ── state ──────────────────────────────────────────────────────────
          let pendingRange = null;   // { start, end, text } waiting for a label
          let activeTooltip = null;

          // ── helpers ────────────────────────────────────────────────────────
          const LABEL_COLORS = [
            "#ef476f","#f7b731","#26de81","#45aaf2",
            "#a55eea","#fd9644","#2bcbba","#fc5c65",
          ];
          function labelColor(label) {
            const labels = model.get("labels");
            const idx = labels.indexOf(label);
            return LABEL_COLORS[idx % LABEL_COLORS.length];
          }
          function hexToRgba(hex, alpha) {
            const r = parseInt(hex.slice(1,3),16);
            const g = parseInt(hex.slice(3,5),16);
            const b = parseInt(hex.slice(5,7),16);
            return `rgba(${r},${g},${b},${alpha})`;
          }

          // ── build skeleton ─────────────────────────────────────────────────
          el.innerHTML = `
            <style>
              .ta-wrap { display:flex; gap:16px; }
              .ta-editor { flex:1; min-width:0; }
              .ta-sidebar { width:220px; flex-shrink:0; }

              .ta-prose { 
                line-height:1.75; padding:16px; border:1px solid #e2e8f0;
                border-radius:8px; background:#fff; min-height:120px;
                cursor:text; user-select:text;
              }
              .ta-prose mark {
                border-radius:3px; padding:1px 0; cursor:pointer;
                transition: filter .15s;
              }
              .ta-prose mark:hover { filter: brightness(.88); }

              /* floating label picker */
              .ta-picker {
                position:fixed; z-index:9999;
                background:#fff; border:1px solid #cbd5e1;
                border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,.15);
                padding:8px; display:none; flex-direction:column; gap:6px;
                min-width:170px;
              }
              .ta-picker.visible { display:flex; }
              .ta-picker-title { font-size:11px; color:#64748b; font-weight:600;
                text-transform:uppercase; letter-spacing:.05em; padding-bottom:2px;
                border-bottom:1px solid #f1f5f9; margin-bottom:2px; }
              .ta-picker button {
                border:none; background:transparent; text-align:left;
                padding:5px 8px; border-radius:5px; cursor:pointer;
                font-size:13px; display:flex; align-items:center; gap:6px;
              }
              .ta-picker button:hover { background:#f8fafc; }
              .ta-picker-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
              .ta-picker-cancel { color:#94a3b8 !important; font-size:12px !important; }

              /* sidebar */
              .ta-sidebar h3 { font-size:13px; color:#475569; font-weight:600;
                margin:0 0 8px; text-transform:uppercase; letter-spacing:.05em; }
              .ta-anno-list { list-style:none; margin:0; padding:0; display:flex;
                flex-direction:column; gap:6px; }
              .ta-anno-item {
                background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px;
                padding:8px 10px; font-size:12px; position:relative;
              }
              .ta-anno-quote { color:#334155; margin-bottom:4px;
                white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
              .ta-anno-badge {
                display:inline-block; border-radius:99px; padding:1px 8px;
                font-size:11px; font-weight:600; color:#fff;
              }
              .ta-anno-del {
                position:absolute; top:6px; right:8px; cursor:pointer;
                color:#94a3b8; font-size:15px; line-height:1;
                background:none; border:none; padding:0;
              }
              .ta-anno-del:hover { color:#ef476f; }

              .ta-empty { color:#94a3b8; font-size:12px; font-style:italic; }
              .ta-clear { margin-top:10px; font-size:12px; color:#ef476f;
                background:none; border:none; cursor:pointer; padding:0; }
              .ta-clear:hover { text-decoration:underline; }

              .ta-legend { margin-top:16px; }
              .ta-legend h3 { font-size:13px; color:#475569; font-weight:600;
                margin:0 0 6px; text-transform:uppercase; letter-spacing:.05em; }
              .ta-legend-item { display:flex; align-items:center; gap:6px;
                font-size:12px; color:#475569; margin-bottom:4px; }
              .ta-legend-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
            </style>

            <div class="ta-wrap">
              <div class="ta-editor">
                <div class="ta-prose" id="prose"></div>
              </div>
              <div class="ta-sidebar">
                <h3>Annotations</h3>
                <ul class="ta-anno-list" id="anno-list"></ul>
                <button class="ta-clear" id="clear-btn" style="display:none">
                  ✕ Clear all
                </button>
                <div class="ta-legend" id="legend"></div>
              </div>
            </div>

            <div class="ta-picker" id="picker">
              <div class="ta-picker-title">Add label</div>
            </div>
          `;

          const prose    = el.querySelector("#prose");
          const annoList = el.querySelector("#anno-list");
          const clearBtn = el.querySelector("#clear-btn");
          const picker   = el.querySelector("#picker");
          const legend   = el.querySelector("#legend");

          // ── render prose (markdown) ────────────────────────────────────────
          function renderProse() {
            const md = model.get("markdown_text") || "";
            prose.innerHTML = marked.parse(md);
            applyHighlights();
          }

          // ── highlight annotations on prose ─────────────────────────────────
          function applyHighlights() {
            const annotations = model.get("annotations") || [];
            if (!annotations.length) return;

            // Walk text nodes and wrap matches
            const fullText = prose.innerText;

            // We rebuild highlights by wrapping text nodes
            // Reset prose first to plain rendered markdown
            const md = model.get("markdown_text") || "";
            prose.innerHTML = marked.parse(md);

            annotations.forEach((ann, idx) => {
              const color = labelColor(ann.label);
              highlightTextInElement(prose, ann.text, color, idx);
            });
          }

          function highlightTextInElement(root, searchText, color, annIdx) {
            const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            const nodes = [];
            while (walker.nextNode()) nodes.push(walker.currentNode);

            for (const node of nodes) {
              const idx = node.nodeValue.indexOf(searchText);
              if (idx === -1) continue;
              const before = node.nodeValue.slice(0, idx);
              const after  = node.nodeValue.slice(idx + searchText.length);
              const mark = document.createElement("mark");
              mark.textContent = searchText;
              mark.style.background = hexToRgba(color, 0.35);
              mark.style.borderBottom = `2px solid ${color}`;
              mark.dataset.annIdx = annIdx;
              mark.title = `[${(model.get("annotations")[annIdx] || {}).label}] Click to remove`;
              mark.addEventListener("click", e => {
                e.stopPropagation();
                removeAnnotation(parseInt(mark.dataset.annIdx));
              });
              const parent = node.parentNode;
              parent.insertBefore(document.createTextNode(before), node);
              parent.insertBefore(mark, node);
              parent.insertBefore(document.createTextNode(after), node);
              parent.removeChild(node);
              break; // one match per node pass
            }
          }

          // ── selection → picker ─────────────────────────────────────────────
          prose.addEventListener("mouseup", e => {
            const sel = window.getSelection();
            if (!sel || sel.isCollapsed) return;
            const text = sel.toString().trim();
            if (!text) return;

            // Store range info
            pendingRange = { text };

            // Position picker near the mouse
            showPicker(e.clientX, e.clientY);
            e.stopPropagation();
          });

          document.addEventListener("mousedown", e => {
            if (!picker.contains(e.target)) hidePicker();
          });

          function showPicker(x, y) {
            // Rebuild label buttons
            const labels = model.get("labels") || [];
            // Keep title, remove old buttons
            while (picker.children.length > 1) picker.removeChild(picker.lastChild);

            labels.forEach(label => {
              const btn = document.createElement("button");
              const dot = document.createElement("span");
              dot.className = "ta-picker-dot";
              dot.style.background = labelColor(label);
              btn.appendChild(dot);
              btn.appendChild(document.createTextNode(label));
              btn.addEventListener("mousedown", ev => {
                ev.preventDefault();
                addAnnotation(pendingRange.text, label);
                hidePicker();
              });
              picker.appendChild(btn);
            });

            const cancelBtn = document.createElement("button");
            cancelBtn.className = "ta-picker-cancel";
            cancelBtn.textContent = "✕  Cancel";
            cancelBtn.addEventListener("mousedown", ev => { ev.preventDefault(); hidePicker(); });
            picker.appendChild(cancelBtn);

            // Position
            const vw = window.innerWidth, vh = window.innerHeight;
            picker.style.left = Math.min(x + 8, vw - 200) + "px";
            picker.style.top  = Math.min(y + 8, vh - 200) + "px";
            picker.classList.add("visible");
          }

          function hidePicker() {
            picker.classList.remove("visible");
            pendingRange = null;
            window.getSelection()?.removeAllRanges();
          }

          // ── annotation CRUD ────────────────────────────────────────────────
          function addAnnotation(text, label) {
            const annotations = [...(model.get("annotations") || [])];
            annotations.push({ text, label, id: Date.now() });
            model.set("annotations", annotations);
            model.save_changes();
            refreshSidebar();
            applyHighlights();
          }

          function removeAnnotation(idx) {
            const annotations = [...(model.get("annotations") || [])];
            annotations.splice(idx, 1);
            model.set("annotations", annotations);
            model.save_changes();
            refreshSidebar();
            applyHighlights();
          }

          function clearAll() {
            model.set("annotations", []);
            model.save_changes();
            refreshSidebar();
            applyHighlights();
          }

          // ── sidebar refresh ────────────────────────────────────────────────
          function refreshSidebar() {
            const annotations = model.get("annotations") || [];
            annoList.innerHTML = "";

            if (!annotations.length) {
              const li = document.createElement("li");
              li.className = "ta-empty";
              li.textContent = "Select text to annotate.";
              annoList.appendChild(li);
              clearBtn.style.display = "none";
            } else {
              annotations.forEach((ann, i) => {
                const li = document.createElement("li");
                li.className = "ta-anno-item";
                const color = labelColor(ann.label);
                li.innerHTML = `
                  <div class="ta-anno-quote">"${ann.text}"</div>
                  <span class="ta-anno-badge" style="background:${color}">${ann.label}</span>
                  <button class="ta-anno-del" data-idx="${i}">×</button>
                `;
                li.querySelector(".ta-anno-del").addEventListener("click", () => removeAnnotation(i));
                annoList.appendChild(li);
              });
              clearBtn.style.display = "inline";
            }

            // Legend
            const labels = model.get("labels") || [];
            legend.innerHTML = `<h3>Labels</h3>` +
              labels.map(l => `
                <div class="ta-legend-item">
                  <span class="ta-legend-dot" style="background:${labelColor(l)}"></span>${l}
                </div>`).join("");
          }

          clearBtn.addEventListener("click", clearAll);

          // ── react to model changes ─────────────────────────────────────────
          model.on("change:markdown_text", renderProse);
          model.on("change:labels", () => { refreshSidebar(); applyHighlights(); });
          model.on("change:annotations", () => { refreshSidebar(); applyHighlights(); });

          // ── initial render ─────────────────────────────────────────────────
          renderProse();
          refreshSidebar();
        }

        export default { render };
        """

        markdown_text = traitlets.Unicode("").tag(sync=True)
        labels = traitlets.List(traitlets.Unicode(), [
            "Hallucination", "Unnecessary", "Too verbose",
            "Factual error", "Biased", "Missing context"
        ]).tag(sync=True)
        annotations = traitlets.List(traitlets.Dict(), []).tag(sync=True)

    return (TextAnnotatorWidget,)


@app.cell
def _(TextAnnotatorWidget, response):
    TextAnnotatorWidget(
        labels=["hallucination", "personal information", "too verbose", "high priority", "low priority"],
        markdown_text=response
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
