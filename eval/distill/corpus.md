# Distillation corpus (DESIGN §8, G7)

The classifier that will replace the local LLM pass is trained on Claude's zone labels over
an *unlabeled* corpus and evaluated on the held-out labeled set in `eval/zoning/labeled/`
(ADR-013). This file is the corpus: where every document comes from, under what licence,
and the rules for adding one. `collect.py` reads the manifest below and downloads the
documents into `eval/results/local/distill/` (gitignored); `label.py` labels them.

## Rules for a document

- **Public and redistributable.** US federal works (public domain), UK Crown copyright under
  the Open Government Licence v3, IETF RFCs (IETF Trust legal provisions: the text may be
  copied and distributed), Creative Commons (BY, BY-SA, BY-NC-SA), MIT / Apache / BSD /
  Unlicense project files, and CC BY arXiv papers. Nothing under an "all rights reserved" or
  arXiv non-exclusive licence, nothing behind a login, nothing scraped against a site's terms.
- **Of the kinds in the labeled set**: course syllabi and assignments, lecture notes and
  tutorials, specs and RFCs, READMEs and manuals, RFPs and procurement guides, grant calls,
  policies and terms, contracts, press releases, minutes, articles, papers, release notes,
  FAQs, newsletters, landing pages. No kind should be more than a fifth of the corpus.
- **No personal data.** Sources are institutional pages and project files, not personal
  blogs, mailing-list mail, résumés or issue threads. Names that appear are professional
  attribution (authors, officials, maintainers). `collect.py` still redacts every e-mail
  address and phone number it finds, so none reaches the corpus or a prompt.
- **Not in the labeled set.** The labeled set is authored, this corpus is real; nothing is
  shared between them, so the evaluation stays held out.
- **Whole documents**, in the format the source serves (`.txt`, `.md`, `.rst` as text,
  `.html`), so the segmenter sees real headings, navigation and footers. Text files longer
  than `MAX_CHARS` (60 000) are cut at a paragraph boundary and marked `truncated` in the
  manifest `collect.py` writes.

## Manifest

One row per document. `collect.py` parses this table. `id` is the file stem; `format` the
suffix the file is saved with; `kind` one of the labeled-set kinds.

| id | kind | format | licence | url |
|---|---|---|---|---|
| rfc2119-keywords | spec | txt | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc2119.txt |
| rfc8259-json | spec | txt | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc8259.txt |
| rfc7396-merge-patch | spec | txt | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc7396.txt |
| rfc6902-json-patch | spec | txt | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc6902.txt |
| rfc9457-problem-details | spec | txt | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc9457.txt |
| pep8-style-guide | spec | txt | Public domain (PEP) | https://raw.githubusercontent.com/python/peps/main/peps/pep-0008.rst |
| readme-requests | readme | md | Apache-2.0 | https://raw.githubusercontent.com/psf/requests/main/README.md |
| readme-ripgrep | readme | md | Unlicense / MIT | https://raw.githubusercontent.com/BurntSushi/ripgrep/master/README.md |
| readme-fastapi | readme | md | MIT | https://raw.githubusercontent.com/fastapi/fastapi/master/README.md |
| readme-ruff | readme | md | MIT | https://raw.githubusercontent.com/astral-sh/ruff/main/README.md |
| readme-uv | readme | md | Apache-2.0 / MIT | https://raw.githubusercontent.com/astral-sh/uv/main/README.md |
| readme-ollama | readme | md | MIT | https://raw.githubusercontent.com/ollama/ollama/main/README.md |
| manual-ollama-api | manual | md | MIT | https://raw.githubusercontent.com/ollama/ollama/main/docs/api.md |
| manual-uv-projects | manual | md | Apache-2.0 / MIT | https://raw.githubusercontent.com/astral-sh/uv/main/docs/guides/projects.md |
| contributing-ruff | policy | md | MIT | https://raw.githubusercontent.com/astral-sh/ruff/main/CONTRIBUTING.md |
| security-nodejs | policy | md | MIT | https://raw.githubusercontent.com/nodejs/node/main/SECURITY.md |
| coc-contributor-covenant | policy | md | CC BY 4.0 | https://raw.githubusercontent.com/EthicalSource/contributor_covenant/release/content/version/2/1/code_of_conduct.md |
| policy-github-aup | policy | md | CC BY 4.0 | https://raw.githubusercontent.com/github/docs/main/content/site-policy/acceptable-use-policies/github-acceptable-use-policies.md |
| policy-govuk-genai-framework | ai_policy | html | OGL v3 | https://www.gov.uk/government/publications/generative-ai-framework-for-hmg/generative-ai-framework-for-hmg-html |
| policy-govuk-genai-education | ai_policy | html | OGL v3 | https://www.gov.uk/government/publications/generative-artificial-intelligence-in-education/generative-artificial-intelligence-ai-in-education |
| terms-github | terms | md | CC BY 4.0 | https://raw.githubusercontent.com/github/docs/main/content/site-policy/github-terms/github-terms-of-service.md |
| contract-apache-license | contract | txt | Apache-2.0 (the licence text) | https://www.apache.org/licenses/LICENSE-2.0.txt |
| contract-far-52-212-4 | contract | html | Public domain (US federal) | https://www.acquisition.gov/far/52.212-4 |
| rfp-18f-procurement-language | rfp | md | Public domain (CC0) | https://raw.githubusercontent.com/18F/API-All-the-X/master/pages/procurement_language.md |
| rfp-18f-solicitation-guide | rfp | md | Public domain (CC0) | https://raw.githubusercontent.com/18F/18f.gsa.gov/main/content/posts/2019-08-20-an-agile-software-development-solicitation-guide.md |
| rfp-18f-buying-dev-services | rfp | md | Public domain (CC0) | https://raw.githubusercontent.com/18F/guides/main/content/derisking-government-tech/home/buying-development-services.md |
| rfp-18f-ads-ordering-guide | rfp | md | Public domain (CC0) | https://raw.githubusercontent.com/18F/ads-bpa/18f-pages/_pages/ordering-guide.md |
| grant-nih-pa-20-185 | grant_call | html | Public domain (US federal) | https://grants.nih.gov/grants/guide/pa-files/PA-20-185.html |
| grant-nih-par-23-079 | grant_call | html | Public domain (US federal) | https://grants.nih.gov/grants/guide/pa-files/PAR-23-079.html |
| press-nasa-crew-9 | press_release | html | Public domain (US federal) | https://www.nasa.gov/news-release/nasa-sets-coverage-for-agencys-spacex-crew-9-launch-docking/ |
| press-nist-pqc | press_release | html | Public domain (US federal) | https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards |
| press-govuk-anglian-water | press_release | html | OGL v3 | https://www.gov.uk/government/news/16m-fine-for-anglian-waters-pollution-of-essex-river |
| press-govuk-octopus | press_release | html | OGL v3 | https://www.gov.uk/government/news/octopus-explosion-off-south-west-prompts-talks-between-fishermen-and-scientists |
| minutes-fomc-2024-01 | minutes | html | Public domain (US federal) | https://www.federalreserve.gov/monetarypolicy/fomcminutes20240131.htm |
| article-wiki-prompt-injection | article | html | CC BY-SA 4.0 | https://en.wikipedia.org/wiki/Prompt_injection |
| article-wiki-rfp | article | html | CC BY-SA 4.0 | https://en.wikipedia.org/wiki/Request_for_proposal |
| article-18f-rfps | article | md | Public domain (CC0) | https://raw.githubusercontent.com/18F/18f.gsa.gov/main/content/posts/2016-10-03-using-rfps-make-every-dollar-count.md |
| article-turing-way-definitions | article | md | CC BY 4.0 | https://raw.githubusercontent.com/the-turing-way/the-turing-way/main/book/website/reproducible-research/overview/overview-definitions.md |
| guide-digitalgov-plain-language | manual | html | Public domain (US federal) | https://digital.gov/guides/plain-language |
| paper-arxiv-2306-05499 | paper | html | CC BY 4.0 | https://arxiv.org/html/2306.05499 |
| paper-arxiv-2406-14048 | paper | html | CC BY 4.0 | https://arxiv.org/html/2406.14048 |
| lecture-missing-semester-shell | lecture | md | CC BY-NC-SA 4.0 | https://raw.githubusercontent.com/missing-semester/missing-semester/master/_2020/shell-tools.md |
| lecture-missing-semester-git | lecture | md | CC BY-NC-SA 4.0 | https://raw.githubusercontent.com/missing-semester/missing-semester/master/_2020/version-control.md |
| tutorial-rust-book-data-types | tutorial | md | Apache-2.0 / MIT | https://raw.githubusercontent.com/rust-lang/book/main/src/ch03-02-data-types.md |
| tutorial-rust-book-result | tutorial | md | Apache-2.0 / MIT | https://raw.githubusercontent.com/rust-lang/book/main/src/ch09-02-recoverable-errors-with-result.md |
| tutorial-django-01 | tutorial | txt | BSD-3-Clause | https://raw.githubusercontent.com/django/django/main/docs/intro/tutorial01.txt |
| tutorial-git | tutorial | txt | GPL-2.0 | https://raw.githubusercontent.com/git/git/master/Documentation/gittutorial.adoc |
| tutorial-carpentries-shell-intro | tutorial | md | CC BY 4.0 | https://raw.githubusercontent.com/swcarpentry/shell-novice/main/episodes/01-intro.md |
| tutorial-carpentries-numpy | tutorial | md | CC BY 4.0 | https://raw.githubusercontent.com/swcarpentry/python-novice-inflammation/main/episodes/02-numpy.md |
| tutorial-github-create-repo | tutorial | md | CC BY 4.0 | https://raw.githubusercontent.com/github/docs/main/content/get-started/start-your-journey/creating-a-repository-for-your-project-on-github.md |
| syllabus-ocw-6-0001 | syllabus | html | CC BY-NC-SA 4.0 | https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/pages/syllabus/ |
| syllabus-cs50x-2024 | syllabus | html | CC BY-NC-SA 4.0 | https://cs50.harvard.edu/x/2024/syllabus/ |
| assignment-ocw-6-0001 | assignment | html | CC BY-NC-SA 4.0 | https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/pages/assignments/ |
| assignment-cs50x-pset1 | assignment | html | CC BY-NC-SA 4.0 | https://cs50.harvard.edu/x/2024/psets/1/ |
| assignment-cs50x-mario | assignment | html | CC BY-NC-SA 4.0 | https://cs50.harvard.edu/x/2024/psets/1/mario/less/ |
| release-notes-rust-1-80 | release_notes | html | Apache-2.0 / MIT | https://blog.rust-lang.org/2024/07/25/Rust-1.80.0/ |
| faq-python-general | faq | html | PSF-2.0 | https://docs.python.org/3/faq/general.html |
| newsletter-this-week-in-rust | newsletter | md | Apache-2.0 / MIT | https://raw.githubusercontent.com/rust-lang/this-week-in-rust/master/content/2024-10-16-this-week-in-rust.md |
| landing-rust-lang | landing_page | html | Apache-2.0 / MIT | https://www.rust-lang.org/ |

Licence notes: IETF RFCs carry the IETF Trust's legal provisions (BCP 78), which permit
copying and distributing the text. PEPs are placed in the public domain by their authors.
GitHub's `docs` content is CC BY 4.0; 18F work is CC0 (US federal, public domain in any case).
MIT OpenCourseWare and CS50 are CC BY-NC-SA 4.0 (non-commercial: fine for an evaluation
corpus, and the corpus is not redistributed by this repo). The Rust book, blog and
*This Week in Rust* are dual MIT / Apache-2.0. Wikipedia is CC BY-SA 4.0. The arXiv papers are
the two whose authors chose CC BY 4.0 (checked on their abstract pages). GOV.UK pages are
Crown copyright under the Open Government Licence v3.
