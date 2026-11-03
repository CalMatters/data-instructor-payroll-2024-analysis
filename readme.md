# Investigate instructor pay

An analysis of pay data to find instructors teaching at multiple campuses using compensation data from the public higher education system. This repo contains code for the processing and analysis pipeline. For the full narrative methodology and findings, see [TK Show Your Work TK](/).

## Data sources

1. Payroll data shared with CalMatters by [Transparent California](https://transparentcalifornia.com/)
2. Course catalog, faculty directory and employment data gathered by CalMatters via public sources on the web or direct request sent to campuses

## Quick start

This project uses [Marimo](https://marimo.io/) (an interactive Python notebook) and [uv](https://github.com/astral-sh/uv) (a fast Python package manager).

### Setup (first time only)

1. **Install uv and just** (if not already installed):

   ```bash
   brew install uv
   brew install just
   ```

2. **Install dependencies**:

   ```bash
   uv sync
   ```

3. Run notebooks:

   ```bash
   uv run marimo NOTEBOOK_FILE_NAME.py
   ```

## Data processing workflow

The notebooks follow a semi-sequential pipeline:

1. `00_cluster_build.py`: Reads in the raw payroll data, normalizes the key data fields, clusters community college records based on employee name; cross-references human-reviewed clusters against CSU and UC payroll data
2. `01_cluster_review.py`: Reads in the human-reviewed clusters and runs a series of validations to confirm the payroll records clusters identified as a single entity meet our expected standards for verification
3. `02_fact_check.py`: Reads in the human-reviewed clusters and the raw payroll data to fact check published findings

### Reviewed cluster sample

To protect the privacy of instructors not named in our reporting, we are not publishing our full set of human-reviewed clusters. `data/calmatters_review/reviewed-clusters-sample.json` contains the confirmed clusters for the 10 highest-paid instructors plus every other instructor named in the story. All three notebooks run against it.

The screenshots and documents we used as evidence for these instructors are saved in `data/calmatters_review/evidence/{instructor}/{employer}/`, and the sample links to them by repo path. `evidence/manifest.csv` lists which directory page or course each file supports.

Some courses were confirmed by searching colleges' full 2024 class schedules rather than by screenshot. `data/course-schedules/` has those sections and the raw schedule files they came from; see its readme.

Checks on individual instructors match the published story. Figures that count or summarize all instructors (totals, medians, percentiles, the histogram) reflect only the sample, so `02_fact_check.py` lists the full-data result next to each one.

To reproduce the full analysis, export the candidate clusters from `00_cluster_build.py` and do your own review. Each reviewed cluster needs a `verdict` (`"real"` for confirmed instructors) and a `groups[0]` entry holding the confirmed payroll `records`, any confirmed UC/CSU `crossLinks` and the `verification` evidence. See the sample file for the exact fields the notebooks read.

## Data use

While the contents of this repo are shared under an Apache 2.0 license, CalMatters/The Markup would appreciate any credit or attribution you're willing to give. We're also interested to learn how you used it, so feel free to [send us a message](john@calmatters.org) or open an issue if you do. If you have any questions, feel free to [contact us](john@calmatters.org) as well.

CalMatters is a nonpartisan, nonprofit journalism venture committed to explaining how California’s state Capitol works and why it matters.

## Contact and issues

For bugs, unclear documentation, or questions about the pipeline, use [TK GitHub Issues TK](/) or send us an [email](data@calmatters.org).

## Note on AI-assisted work

We used AI coding tools to assist with the analysis. All results were manually reviewed by a member of our team.

## License

Code in this repository is licensed under the Apache License, Version 2.0; see [LICENSE](LICENSE). Dependency licenses are managed by PyPI packages; see [NOTICE](NOTICE).
