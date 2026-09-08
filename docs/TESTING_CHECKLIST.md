# Manual testing checklist

Automated tests do not call Claude. This checklist uses a small number of real API requests.
Start with the included demo note and the budget model.

## Setup and safety

- [ ] App starts with `python -m streamlit run app.py`.
- [ ] Without a key, generation is blocked with a clear message.
- [ ] The real `.streamlit/secrets.toml` does not appear in `git status`.
- [ ] The sidebar defaults to Claude Haiku 4.5 and shows a 12,000-token input cap.

## Input

- [ ] **Use demo notes** fills the paste field.
- [ ] A normal TXT or Markdown file extracts correctly.
- [ ] A text-based PDF extracts readable text and page labels.
- [ ] A DOCX and a PPTX extract their visible text.
- [ ] An empty, unsupported, oversized, encrypted, or scanned file shows a useful error.

## Four modes

- [ ] Summary has a big picture, key ideas, terms/formulas, connections, mistakes, and review.
- [ ] Practice questions appear before the hidden answer-key expander.
- [ ] Concept explanation moves from intuition to an example and technical detail.
- [ ] Socratic Mode begins with one diagnostic question and does not reveal the answer early.
- [ ] **I’m stuck** returns one smaller hint.
- [ ] **Reveal and explain now** gives reasoning and ends with a transfer question.

## Budgets and state

- [ ] Each successful generation increments the session request meter by one.
- [ ] Actual input/output token counts appear with the response.
- [ ] Lowering the input cap on a long note causes a visible sampling warning.
- [ ] Changing notes during Socratic Mode requires a new guided session.
- [ ] Downloaded Markdown contains the expected result/transcript.

## Quality questions for the project owner

- [ ] Is the summary accurate compared with the original note?
- [ ] Are quiz distractors plausible rather than obvious?
- [ ] Is the explanation appropriate for the selected study level?
- [ ] Does Socratic Mode help thinking without becoming frustrating?
- [ ] Would you show this exact version in a Campus Ambassador application?
