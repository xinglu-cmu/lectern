# Real documents in the labeled set (v0.4)

Added 2026-10-23: redistributable public documents of the labeled set's kinds, labeled by phrase by hand. None of them is in `eval/distill/corpus.md`, so the distilled classifier never saw them. E-mail addresses and phone numbers are redacted; text files longer than 25 000 characters are cut at a paragraph boundary. Files are `real-<id>.<ext>`; authored documents have no prefix.

| file | kind | licence | source |
|---|---|---|---|
| `real-rfc8615-well-known.txt` | spec | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc8615.txt (cut at 25k chars) |
| `real-rfc3339-timestamps.txt` | spec | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc3339.txt (cut at 25k chars) |
| `real-rfc7493-i-json.txt` | spec | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc7493.txt |
| `real-rfc6901-json-pointer.txt` | spec | IETF Trust (RFC) | https://www.rfc-editor.org/rfc/rfc6901.txt |
| `real-pep257-docstrings.txt` | spec | Public domain (PEP) | https://raw.githubusercontent.com/python/peps/main/peps/pep-0257.rst |
| `real-pep20-zen.txt` | spec | Public domain (PEP) | https://raw.githubusercontent.com/python/peps/main/peps/pep-0020.rst |
| `real-readme-httpx.md` | readme | BSD-3-Clause | https://raw.githubusercontent.com/encode/httpx/master/README.md |
| `real-readme-markitdown.md` | readme | MIT | https://raw.githubusercontent.com/microsoft/markitdown/main/README.md |
| `real-readme-cpython.txt` | readme | PSF-2.0 | https://raw.githubusercontent.com/python/cpython/main/README.rst |
| `real-readme-anthropic-sdk.md` | readme | MIT | https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/README.md |
| `real-readme-pydantic.md` | readme | MIT | https://raw.githubusercontent.com/pydantic/pydantic/main/README.md |
| `real-readme-rich.md` | readme | MIT | https://raw.githubusercontent.com/Textualize/rich/master/README.md |
| `real-guide-digitalgov-site-scanning.html` | manual | Public domain (US federal) | https://digital.gov/guides/site-scanning/ |
| `real-manual-github-security-features.md` | manual | CC BY 4.0 | https://raw.githubusercontent.com/github/docs/main/content/code-security/getting-started/github-security-features.md |
| `real-manual-uv-scripts.md` | manual | Apache-2.0 / MIT | https://raw.githubusercontent.com/astral-sh/uv/main/docs/guides/scripts.md |
| `real-policy-requests-security.md` | policy | Apache-2.0 | https://raw.githubusercontent.com/psf/requests/main/.github/SECURITY.md |
| `real-contract-far-52-204-21.html` | contract | Public domain (US federal) | https://www.acquisition.gov/far/52.204-21 |
| `real-policy-github-community-guidelines.md` | policy | CC BY 4.0 | https://raw.githubusercontent.com/github/docs/main/content/site-policy/github-terms/github-community-guidelines.md |
| `real-terms-github-events.md` | terms | CC BY 4.0 | https://raw.githubusercontent.com/github/docs/main/content/site-policy/github-terms/github-event-terms.md |
| `real-press-govuk-gbr-chair.html` | press_release | OGL v3 | https://www.gov.uk/government/news/sir-john-kingman-appointed-as-great-british-railways-chair |
| `real-press-govuk-inquest-training.html` | press_release | OGL v3 | https://www.gov.uk/government/news/approved-training-course-for-inquests |
| `real-minutes-fomc-2025-01.html` | minutes | Public domain (US federal) | https://www.federalreserve.gov/monetarypolicy/fomcminutes20250129.htm |
| `real-article-wiki-syllabus.html` | article | CC BY-SA 4.0 | https://en.wikipedia.org/wiki/Syllabus |
| `real-article-wiki-rfi.html` | article | CC BY-SA 4.0 | https://en.wikipedia.org/wiki/Request_for_information |
| `real-article-turing-way-open-data.md` | article | CC BY 4.0 | https://raw.githubusercontent.com/the-turing-way/the-turing-way/main/book/website/reproducible-research/open/open-data.md |
| `real-lecture-missing-semester-debugging.md` | lecture | CC BY-NC-SA 4.0 | https://raw.githubusercontent.com/missing-semester/missing-semester/master/_2020/debugging-profiling.md (cut at 25k chars) |
| `real-tutorial-rust-book-install.md` | tutorial | Apache-2.0 / MIT | https://raw.githubusercontent.com/rust-lang/book/main/src/ch01-01-installation.md |
| `real-tutorial-django-02.txt` | tutorial | BSD-3-Clause | https://raw.githubusercontent.com/django/django/main/docs/intro/tutorial02.txt |
| `real-tutorial-carpentries-shell-filedir.md` | tutorial | CC BY 4.0 | https://raw.githubusercontent.com/swcarpentry/shell-novice/main/episodes/02-filedir.md (cut at 25k chars) |
| `real-article-github-what-is-github.md` | article | CC BY 4.0 | https://raw.githubusercontent.com/github/docs/main/content/get-started/start-your-journey/what-is-github.md |
| `real-syllabus-ocw-18-06.html` | syllabus | CC BY-NC-SA 4.0 | https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/pages/syllabus/ |
| `real-syllabus-ocw-6-042j.html` | syllabus | CC BY-NC-SA 4.0 | https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/pages/syllabus/ |
| `real-assignment-cs50x-pset2.html` | assignment | CC BY-NC-SA 4.0 | https://cs50.harvard.edu/x/2024/psets/2/ |
| `real-release-notes-rust-1-84.html` | release_notes | Apache-2.0 / MIT | https://blog.rust-lang.org/2025/01/09/Rust-1.84.0/ |
| `real-faq-git.html` | faq | GPL-2.0 | https://git-scm.com/docs/gitfaq |
| `real-newsletter-this-week-in-rust-2025-01.md` | newsletter | Apache-2.0 / MIT | https://raw.githubusercontent.com/rust-lang/this-week-in-rust/master/content/2025-01-15-this-week-in-rust.md (cut at 25k chars) |
| `real-landing-ruff-docs.html` | landing_page | MIT | https://docs.astral.sh/ruff/ |
| `real-policy-govuk-data-ethics.html` | policy | OGL v3 | https://www.gov.uk/government/publications/data-ethics-framework/data-ethics-framework-2020 |
