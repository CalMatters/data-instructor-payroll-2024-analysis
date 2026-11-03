import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    from collections import defaultdict
    from dataclasses import dataclass
    from itertools import combinations
    import re

    import marimo as mo
    import pandas as pd
    from rapidfuzz import fuzz

    return combinations, dataclass, defaultdict, fuzz, json, mo, pd, re


@app.cell
def _():
    PAY_COLUMNS = [
        "Base Pay",
        "Overtime Pay",
        "Other Pay",
    ]
    BENEFITS_COLUMNS = [
        "Benefits",
        # "Pension Debt", ## field only available in CC data
    ]
    TOTAL_PAY_PLUS_BENEFITS_COLUMNS = [*PAY_COLUMNS, *BENEFITS_COLUMNS]
    TOTAL_PAY_AND_BENEFITS_COLUMN = "Total Pay & Benefits"
    return PAY_COLUMNS, TOTAL_PAY_PLUS_BENEFITS_COLUMNS


@app.cell(hide_code=True)
def _(pd):
    def to_native(value):
        """Coerce pandas/numpy scalars (and NaN) to plain JSON-serializable values."""
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            return value.item()
        return value

    return (to_native,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Read data
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Helper functions**
    """)
    return


@app.cell
def _(re):
    def normalize_name(name: str) -> str:
        name = name.lower().replace("-", " ")
        name = re.sub(r"[^a-z\s]", "", name)
        return " ".join(name.split())

    return (normalize_name,)


@app.cell
def _(defaultdict):
    def build_token_index(df, name_col):
        # Bucket records by surname token so we only fuzzy-compare within shared surnames
        index = defaultdict(set)
        for idx, name in df[name_col].items():
            for token in name.split()[1:]:
                index[token].add(idx)
        return index

    return (build_token_index,)


@app.cell
def _(pd):
    WHITESPACE_REGEX = r"[ ]+"

    def clean_object_col_whitespace(df: pd.DataFrame):
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].str.strip()
            if df[col].dtype == "object":
                df[col] = (
                    df[col]
                    .replace(WHITESPACE_REGEX, 0, regex=True)
                    .astype(float)
                )

        return df

    def drop_empty_str_columns(df: pd.DataFrame):
        return df.loc[:, ~(df == "").all()]

    return clean_object_col_whitespace, drop_empty_str_columns


@app.cell
def _(PAY_COLUMNS, TOTAL_PAY_PLUS_BENEFITS_COLUMNS, pd):
    def verify_agg_assumptions(df_pay: pd.DataFrame()):
        assert (
            round(df_pay[PAY_COLUMNS].sum(axis=1), 2) == df_pay["Total Pay"]
        ).all()

        assert (
            round(df_pay[TOTAL_PAY_PLUS_BENEFITS_COLUMNS].sum(axis=1), 2)
            == df_pay["Total Pay & Benefits"]
        ).all()

    return (verify_agg_assumptions,)


@app.cell
def _(mo, normalize_name, pd, verify_agg_assumptions):
    COMMUNITY_COLLEGE_DATA_FP = (
        "./data/transparent-california/2024-community-colleges.csv"
    )
    _dtype = {"id": str, "Year": str}

    DF_CC_PAY = pd.read_csv(
        COMMUNITY_COLLEGE_DATA_FP, sep=";", dtype=_dtype
    ).dropna(axis=1, how="all")

    verify_agg_assumptions(DF_CC_PAY)

    df_cc_pay = DF_CC_PAY.copy()
    df_cc_pay["_job_title"] = df_cc_pay["Job Title"].apply(normalize_name)
    df_cc_pay["_name"] = DF_CC_PAY["Employee Name"].apply(normalize_name)

    mo.vstack([mo.md("## CA Community College pay data"), df_cc_pay])
    return DF_CC_PAY, df_cc_pay


@app.cell
def _(
    clean_object_col_whitespace,
    drop_empty_str_columns,
    mo,
    normalize_name,
    pd,
):
    CSU_DATA_FP = (
        "./data/transparent-california/CY2024 California State University.xlsx"
    )
    _dtype = {"Unique\nID": str}

    DF_CSU_PAY = pd.read_excel(CSU_DATA_FP, dtype=_dtype, skiprows=1).dropna(
        axis=1, how="all"
    )

    df_csu_pay = DF_CSU_PAY.copy()
    df_csu_pay.columns = [col.replace("\n", " ") for col in df_csu_pay.columns]
    df_csu_pay = clean_object_col_whitespace(df_csu_pay)
    df_csu_pay = drop_empty_str_columns(df_csu_pay)
    df_csu_pay["_title"] = df_csu_pay["Class Title"].apply(normalize_name)
    df_csu_pay["_name"] = (
        df_csu_pay["First Name"] + " " + df_csu_pay["Last Name"]
    ).apply(normalize_name)
    df_csu_pay["_agency"] = df_csu_pay["Subdivision Name"].copy()
    # fill empty agency column with the approriate department name
    df_csu_pay.loc[df_csu_pay["_agency"] == "", "_agency"] = df_csu_pay.loc[
        df_csu_pay["_agency"] == "", "Department Name"
    ]

    mo.vstack([mo.md("## California State University pay data"), df_csu_pay])
    return (df_csu_pay,)


@app.cell
def _(mo, normalize_name, pd):
    UC_DATA_FP = "./data/transparent-california/UC AWR_website_data_with_Benefits_CY2024.xlsx"
    _dtype = {"Calendar Year": str}

    def _str_or_empty(value):
        # Blank out NaN and stray non-string values (e.g. booleans in Last Name)
        return value if isinstance(value, str) else ""

    DF_UC_PAY = pd.read_excel(UC_DATA_FP, dtype=_dtype)

    df_uc_pay = DF_UC_PAY.copy()
    _names = df_uc_pay[["First Name", "Last Name"]].map(_str_or_empty)
    df_uc_pay["_name"] = (
        (_names["First Name"] + " " + _names["Last Name"])
        .str.strip()
        .apply(normalize_name)
    )
    df_uc_pay["_title"] = df_uc_pay["Title"].fillna("").apply(normalize_name)

    mo.vstack([mo.md("## University of California pay data"), df_uc_pay])
    return (df_uc_pay,)


@app.cell(hide_code=True)
def _(dataclass, df_cc_pay, df_csu_pay, df_uc_pay, pd):
    @dataclass
    class DatasetConfig:
        label: str
        df: pd.DataFrame
        name_col: (
            str  # display name (raw); use "_name" if no separate raw field
        )
        institution_col: str  # institution / agency
        record_id_col: str  # unique record identifier (None = use index)
        job_title_col: str  # normalized job title
        total_pay_col: str  # total compensation

    DATASET_CONFIGS = {
        "Community College": DatasetConfig(
            label="Community College",
            df=df_cc_pay,
            name_col="Employee Name",
            institution_col="Agency",
            record_id_col="id",
            job_title_col="_job_title",
            total_pay_col="Total Pay",
        ),
        "CSU": DatasetConfig(
            label="CSU",
            df=df_csu_pay,
            name_col="_name",
            institution_col="_agency",
            record_id_col="Unique ID",
            job_title_col="_title",
            total_pay_col="Total Pay",
        ),
        "UC": DatasetConfig(
            label="UC",
            df=df_uc_pay,
            name_col="_name",
            institution_col="Location",
            record_id_col=None,
            job_title_col="_title",
            total_pay_col="Gross Pay",
        ),
    }

    def prepare_for_er(config: DatasetConfig) -> pd.DataFrame:
        """Return a copy of the dataset with canonical column names for the ER pipeline."""
        df = config.df.copy()

        rename_map = {
            config.institution_col: "_institution",
            config.job_title_col: "_job_title",
            config.total_pay_col: "_total_pay",
        }
        if config.record_id_col:
            rename_map[config.record_id_col] = "_record_id"
        else:
            df["_record_id"] = df.index.astype(str)

        # Only rename name_col to _display_name when it's a distinct raw column;
        # when name_col IS "_name", keep _name in place and alias below.
        if config.name_col != "_name":
            rename_map[config.name_col] = "_display_name"

        df = df.rename(columns=rename_map)

        if "_display_name" not in df.columns:
            df["_display_name"] = df["_name"]

        return df

    return DATASET_CONFIGS, prepare_for_er


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Entity Resolution

    This section clustered payroll records as the first step in our entity resolution pipeline. The default settings for the pipeline run on the community college system payroll database. Our final analysis opts to only apply this operation on community college payroll. For the CSU and UC systems, we cross-reference our validated cluster names to find possible matches.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    SIMILARITY_THRESHOLD_DEFAULT = 100
    GIVEN_NAME_THRESHOLD_DEFAULT = 100
    INSTITUTION_THRESHOLD_DEFAULT = 5
    MAX_TOKEN_FREQUENCY_DEFAULT = 500

    similarity_threshold_slider = mo.ui.slider(
        50,
        100,
        step=0.5,
        value=SIMILARITY_THRESHOLD_DEFAULT,
        include_input=True,
        label="Trailing name(s) similarity threshold",
        debounce=True,
    )

    given_name_threshold_slider = mo.ui.slider(
        50,
        100,
        step=0.5,
        value=GIVEN_NAME_THRESHOLD_DEFAULT,
        include_input=True,
        label="First name similarity threshold",
        debounce=True,
    )

    institution_threshold_slider = mo.ui.slider(
        2,
        10,
        value=INSTITUTION_THRESHOLD_DEFAULT,
        include_input=True,
        label="Drop clusters with records with fewer than minimum campus threshold",
    )

    max_token_freq_slider = mo.ui.slider(
        0,
        1000,
        value=MAX_TOKEN_FREQUENCY_DEFAULT,
        include_input=True,
        label="Filter out names with extrememely high frequency",
        debounce=True,
    )
    return (
        given_name_threshold_slider,
        institution_threshold_slider,
        max_token_freq_slider,
        similarity_threshold_slider,
    )


@app.cell
def _(DATASET_CONFIGS, mo):
    dataset_picker = mo.ui.dropdown(
        options=list(DATASET_CONFIGS.keys()),
        value="Community College",
        label="Dataset",
    )
    dataset_picker
    return (dataset_picker,)


@app.cell
def _(DATASET_CONFIGS, dataset_picker, prepare_for_er):
    df_er = prepare_for_er(DATASET_CONFIGS[dataset_picker.value])
    return (df_er,)


@app.cell
def _(build_token_index, df_er, max_token_freq_slider):
    max_token_freq = max_token_freq_slider.value

    _raw_index = build_token_index(df_er, "_name")

    # Filter out surnames shared by too many records — they don't discriminate between people
    surname_token_index = {
        token: records
        for token, records in _raw_index.items()
        if len(records) <= max_token_freq
    }

    # Retain dropped names
    excluded_token_index = {
        token: records
        for token, records in _raw_index.items()
        if token not in surname_token_index
    }
    return excluded_token_index, max_token_freq, surname_token_index


@app.cell
def _(
    combinations,
    df_er,
    fuzz,
    given_name_threshold_slider,
    similarity_threshold_slider,
    surname_token_index,
):
    PERFECT_MATCH = 100.0

    similarity_threshold = similarity_threshold_slider.value
    given_name_threshold = given_name_threshold_slider.value

    def name_similarity(name_a: str, name_b: str) -> float:
        tokens_a = set(name_a.split())
        tokens_b = set(name_b.split())
        extra = tokens_a.symmetric_difference(tokens_b)  # xor
        significant_extra = [
            token for token in extra if len(token) > 1
        ]  # retain extras that aren't not initials

        subset_check = tokens_a <= tokens_b or tokens_b <= tokens_a
        one_or_less_extra_token = len(significant_extra) <= 1
        if subset_check and one_or_less_extra_token:
            return PERFECT_MATCH

        return fuzz.token_sort_ratio(name_a, name_b)

    def names_likely_match(name_a: str, name_b: str) -> int | None:
        tokens_a, tokens_b = name_a.split(), name_b.split()
        given_name_a, given_name_b = (tokens_a[0], tokens_b[0])
        # defaults to perfect match
        if fuzz.ratio(given_name_a, given_name_b) < given_name_threshold:
            return None
        similarity = name_similarity(name_a, name_b)
        return int(similarity) if similarity >= similarity_threshold else None

    _compared = set()
    candidate_pairs = []

    for token_records in surname_token_index.values():
        for idx_a, idx_b in combinations(sorted(token_records), 2):
            previously_compared_tokens = (idx_a, idx_b) in _compared
            if previously_compared_tokens:
                continue
            _compared.add((idx_a, idx_b))
            score = names_likely_match(
                df_er.at[idx_a, "_name"],
                df_er.at[idx_b, "_name"],
            )
            if score is not None:
                candidate_pairs.append((idx_a, idx_b, score))
    return candidate_pairs, names_likely_match


@app.cell
def _(candidate_pairs, defaultdict):
    class DisjointSet:
        def __init__(self):
            self._parent = dict()

        def find(self, item):
            self._parent.setdefault(item, item)
            while self._parent[item] != item:
                self._parent[item] = self._parent[self._parent[item]]
                item = self._parent[item]
            return item

        def union(self, item_a, item_b):
            self._parent[self.find(item_a)] = self.find(item_b)

        def groups(self):
            clusters = defaultdict(list)
            for item in self._parent:
                clusters[self.find(item)].append(item)
            return dict(clusters)

    def build_clusters(pairs):
        disjoint_set = DisjointSet()
        for idx_a, idx_b, _score in pairs:
            disjoint_set.union(idx_a, idx_b)
        return disjoint_set.groups()

    name_clusters = build_clusters(candidate_pairs)
    return (name_clusters,)


@app.cell
def _(df_er, institution_threshold_slider, name_clusters, pd):
    institution_threshold = institution_threshold_slider.value
    _cluster_frames = []

    for cluster_id, cluster_entry_indices in name_clusters.items():
        cluster_entries = df_er.loc[cluster_entry_indices]
        if cluster_entries["_institution"].nunique() >= institution_threshold:
            _cluster_frames.append(
                cluster_entries.assign(
                    cluster_id=cluster_id,
                    institution_count=cluster_entries[
                        "_institution"
                    ].nunique(),
                )
            )

    multi_institution_candidates = (
        pd.concat(_cluster_frames)
        .sort_values("institution_count", ascending=False)
        .reset_index(drop=True)
        if _cluster_frames
        else pd.DataFrame()
    )
    return institution_threshold, multi_institution_candidates


@app.cell
def _(
    given_name_threshold_slider,
    institution_threshold_slider,
    max_token_freq_slider,
    mo,
    multi_institution_candidates,
    similarity_threshold_slider,
):
    candidate_summary = (
        multi_institution_candidates.groupby("cluster_id")
        .agg(
            name_variations=(
                "_display_name",
                lambda names: " | ".join(sorted(set(names))),
            ),
            institutions=(
                "_institution",
                lambda agencies: " | ".join(sorted(set(agencies))),
            ),
            institution_count=("_institution", "nunique"),
            record_count=("_record_id", "count"),
            title_count=("_job_title", "nunique"),
            total_pay=("_total_pay", "sum"),
            job_titles=(
                "_job_title",
                lambda job_titles: " | ".join(sorted(set(job_titles))),
            ),
        )
        .sort_values("institution_count", ascending=False)
        .reset_index(drop=True)
    )
    candidate_summary["total_pay"] = round(candidate_summary["total_pay"])

    mo.vstack(
        [
            max_token_freq_slider,
            similarity_threshold_slider,
            given_name_threshold_slider,
            institution_threshold_slider,
            mo.md(
                f"**{len(candidate_summary):,} candidate instructors** found across multiple institutions"
            ),
            mo.ui.table(candidate_summary),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Export**

    We exported to JSON to review the cluster records in a custom-built web app. Contact [CalMatters](mailto:data@calmatters.org) for access to the review web app.

    The remainder of this notebook relies on the human-reviewed cluster data. It cross-references a copy of our reviewed clusters with the CSU and UC payroll records to surface possible matches at those systems.
    """)
    return


@app.cell(hide_code=True)
def _(json, mo, multi_institution_candidates):
    def cluster_to_json(i, group):
        campuses = []
        for institution, campus_df in group.groupby("_institution"):
            pay_by_record = (
                campus_df.groupby(["_display_name", "_job_title"])[
                    "_total_pay"
                ]
                .sum()
                .reset_index()
            )
            records = sorted(
                [
                    {
                        "name": r["_display_name"],
                        "title": r["_job_title"],
                        "pay": int(round(r["_total_pay"])),
                    }
                    for _, r in pay_by_record.iterrows()
                ],
                key=lambda r: (r["name"], r["title"]),
            )
            campuses.append({"campus": institution, "records": records})
        campuses.sort(key=lambda c: c["campus"])
        return {
            "id": i,
            "record_count": int(len(group)),
            "campuses": campuses,
            "aggregate_pay": int(round(group["_total_pay"].sum())),
        }

    _cluster_groups = {
        cid: grp
        for cid, grp in multi_institution_candidates.groupby("cluster_id")
    }
    _sorted_ids = sorted(
        _cluster_groups,
        key=lambda cid: _cluster_groups[cid]["_institution"].nunique(),
        reverse=True,
    )

    mo.download(
        json.dumps(
            [
                cluster_to_json(i, _cluster_groups[cid])
                for i, cid in enumerate(_sorted_ids)
            ],
            indent=2,
        ).encode(),
        filename="candidate_summary.json",
        mimetype="application/json",
        label="Export JSON",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Inspect UC & CSU data
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Cross-reference confirmed CC clusters against UC and CSU data

    After exporting the community college clusters and manually reviewing the data for true positive clusters, we imported the human-reviewed clusters (`data/calmatters_review/reviewed-clusters.json`, shipped here as the `reviewed-clusters-sample.json` subset) to cross-reference whether names in clusters determined `real` (true positives) also appear in the UC or CSU pay data. This was a more effective approach than an independent review of each system and significantly more effective than joining all three systems together for a review.
    """)
    return


@app.cell
def _(json, mo, normalize_name):
    REVIEWED_CLUSTERS_FP = "./data/calmatters_review/reviewed-clusters-sample.json"

    with open(REVIEWED_CLUSTERS_FP) as f:
        _reviewed_clusters = json.load(f)

    confirmed_clusters = [
        cluster
        for cluster in _reviewed_clusters
        if cluster.get("verdict") == "real"
    ]

    confirmed_names_by_cluster = {
        cluster["id"]: sorted(
            {
                normalize_name(record["name"])
                for campus in cluster["campuses"]
                for record in campus["records"]
            }
        )
        for cluster in confirmed_clusters
    }

    mo.md(
        f"**{len(confirmed_names_by_cluster)} confirmed clusters** loaded out of {len(_reviewed_clusters)} reviewed"
    )
    return (confirmed_names_by_cluster,)


@app.cell
def _(names_likely_match):
    def find_cross_matches(
        normalized_names, target_df, token_index, name_col="_name"
    ):
        candidate_indices = set()
        for name in normalized_names:
            for trailing_name_token in name.split():
                candidate_indices.update(
                    token_index.get(trailing_name_token, ())
                )

        matches = []
        for idx in candidate_indices:
            target_name = target_df.at[idx, name_col]
            if len(target_name.split()) < 2:
                # Single-token names (missing first or last name, often due to
                # data artifacts like a boolean value in the Last Name column)
                # are too weak to identify a specific person.
                continue
            for name in normalized_names:
                score = names_likely_match(name, target_name)
                if score is not None:
                    matches.append(
                        {
                            "target_index": idx,
                            "score": score,
                            "matched_cc_name": name,
                        }
                    )
                    break
        return matches

    def build_cross_reference(
        confirmed_names_by_cluster, target_df, token_index, name_col="_name"
    ):
        return {
            cluster_id: find_cross_matches(
                names,
                target_df,
                token_index,
                name_col,
            )
            for cluster_id, names in confirmed_names_by_cluster.items()
        }

    return (build_cross_reference,)


@app.cell
def _(
    build_cross_reference,
    build_token_index,
    confirmed_names_by_cluster,
    df_csu_pay,
    df_uc_pay,
):
    uc_token_index = build_token_index(df_uc_pay, "_name")
    csu_token_index = build_token_index(df_csu_pay, "_name")

    cluster_uc_matches = build_cross_reference(
        confirmed_names_by_cluster, df_uc_pay, uc_token_index
    )
    cluster_csu_matches = build_cross_reference(
        confirmed_names_by_cluster, df_csu_pay, csu_token_index
    )
    return cluster_csu_matches, cluster_uc_matches


@app.cell(hide_code=True)
def _(df_uc_pay, to_native):
    def uc_candidate(match):
        """Cleans up UC data record for JSON cluster export"""
        uc_row = df_uc_pay.loc[match["target_index"]]
        return {
            "system": "UC",
            "id": to_native(match["target_index"]),
            "name": f"{uc_row['First Name']} {uc_row['Last Name']}".strip(),
            "title": to_native(uc_row["Title"]),
            "institution": to_native(uc_row["Location"]),
            "pay": to_native(uc_row["Gross Pay"]),
            "unique_id": None,
            "score": match["score"],
            "matched_cc_name": match["matched_cc_name"],
        }

    return (uc_candidate,)


@app.cell(hide_code=True)
def _(df_csu_pay, to_native):
    def csu_candidate(match):
        """Cleans up CSU data record for JSON cluster export"""
        csu_row = df_csu_pay.loc[match["target_index"]]
        return {
            "system": "CSU",
            "id": to_native(match["target_index"]),
            "name": f"{csu_row['First Name']} {csu_row['Last Name']}".strip(),
            "title": to_native(csu_row["Class Title"]),
            "institution": to_native(csu_row["_agency"]),
            "pay": to_native(csu_row["Total Pay"]),
            "unique_id": to_native(csu_row.get("Unique ID")),
            "score": match["score"],
            "matched_cc_name": match["matched_cc_name"],
        }

    return (csu_candidate,)


@app.cell
def _(cluster_csu_matches, cluster_uc_matches, csu_candidate, uc_candidate):
    cross_reference_by_cluster = {}
    for _cluster_id in set(cluster_uc_matches) | set(cluster_csu_matches):
        _candidates = [
            uc_candidate(m) for m in cluster_uc_matches.get(_cluster_id, [])
        ] + [
            csu_candidate(m) for m in cluster_csu_matches.get(_cluster_id, [])
        ]
        if _candidates:
            cross_reference_by_cluster[_cluster_id] = _candidates
    return (cross_reference_by_cluster,)


@app.cell
def _(cross_reference_by_cluster, mo, pd):
    _rows = [
        {"cluster_id": cluster_id, **candidate}
        for cluster_id, candidates in cross_reference_by_cluster.items()
        for candidate in candidates
    ]

    cross_reference_df = (
        pd.DataFrame(_rows)
        .sort_values(
            ["cluster_id", "system", "score"], ascending=[True, True, False]
        )
        .reset_index(drop=True)
        if _rows
        else pd.DataFrame()
    )

    mo.vstack(
        [
            mo.md(
                f"**{len(cross_reference_by_cluster)} confirmed clusters** "
                f"have a possible match in UC or CSU data ({len(_rows)} candidate records)"
            ),
            mo.ui.table(cross_reference_df),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Appendix
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Explore compensation data
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Community college**
    """)
    return


@app.cell
def _(DF_CC_PAY):
    DF_CC_PAY["Total Pay"].describe()
    return


@app.cell
def _(DF_CC_PAY, mo):
    COLUMNS_OF_INTEREST = [
        "Agency",
        "Employee Name",
        "Job Title",
        "Total Pay",
        "Total Pay Pctl",
    ]

    _df_cc_pay = DF_CC_PAY.copy()
    _df_cc_pay["Total Pay Pctl"] = (
        _df_cc_pay["Total Pay"].rank(method="average", pct=True) * 100
    )

    highest_paid_cc_employee_records = DF_CC_PAY.loc[
        DF_CC_PAY.groupby("Agency")["Total Pay"].idxmax()
    ]
    mo.vstack(
        [
            mo.md("Summary statistics:"),
            highest_paid_cc_employee_records["Total Pay"].describe(),
            mo.md(
                "Table filtered for the highest paid employee record at each community college:"
            ),
            highest_paid_cc_employee_records,
            mo.md("All data"),
            _df_cc_pay[COLUMNS_OF_INTEREST],
            mo.md("Job titles for positions in the top 0.1% of total pay"),
            list(
                _df_cc_pay[_df_cc_pay["Total Pay Pctl"] >= 99.9][
                    "Job Title"
                ].unique()
            ),
        ]
    )
    return


@app.cell
def _(DF_CC_PAY, mo):
    # Match titles that *start* with the top executive role, so VPs, assistants,
    # senate/union presidents, and "President's Office" staff fall out
    _CEO_TITLE_REGEX = r"""(?ix)
        ^(?:\d+\s)?                    # payroll code prefix, e.g. "1100 "
        (?:(?:interim|acting|temp|int\.?|int/act|district|college|doctorate,)\s*)?
        (?:superintendent|supt|president|chancellor|chief\ executive\ officer)\b
        (?!'s)                          # not "President's Office" staff
        (?!.*\bvp\b)                    # not "Superintendent/VP" hybrids
    """
    _INTERIM_TITLE_REGEX = r"(?i)\b(?:interim|acting|temp|int)\b"
    # Departing/incoming leaders have no flag in the data, so drop partial-year
    # records by base pay; full-year CEOs start just under $200K, with a gap below
    _FULL_YEAR_BASE_PAY_FLOOR = 180_000

    _job_title = DF_CC_PAY["Job Title"]
    _ceo_records = DF_CC_PAY[
        _job_title.str.contains(_CEO_TITLE_REGEX)
        & ~_job_title.str.contains(_INTERIM_TITLE_REGEX)
        & (DF_CC_PAY["Base Pay"] >= _FULL_YEAR_BASE_PAY_FLOOR)
    ]
    # One leader per agency: in multi-college districts, the chancellor
    cc_ceo_pay = _ceo_records.loc[
        _ceo_records.groupby("Agency")["Total Pay"].idxmax()
    ]

    mo.vstack(
        [
            mo.md(
                f"Median total pay for the top full-year, non-interim leader at "
                f"each of **{len(cc_ceo_pay)}** agencies: "
                f"**${cc_ceo_pay['Total Pay'].median():,.0f}**"
            ),
            cc_ceo_pay["Job Title"].value_counts(),
            cc_ceo_pay,
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **CSU**

    I explored the `Unique ID` field to see if I can catch any employees that match our hypothesis. This approach only produced a single record where a `Unique ID` mapped to five or more campuses. I concluded that if we want instructors paid by five or more campuses, then it is more effective to complete an in-depth analysis of the community college data followed by a cross reference with CSU data.
    """)
    return


@app.cell
def _(df_csu_pay):
    df_csu_pay.groupby(
        "Unique ID",
    ).agg(
        names=(  # unique ID lines up to the same name
            "_name",
            lambda name: " | ".join(sorted(set(name))),
        ),
        title_count=("_title", "nunique"),
        titles=(  # unique ID lines up to the same name
            "_title",
            lambda title: " | ".join(sorted(set(title))),
        ),
        institutions=(
            "_agency",
            lambda agencies: " | ".join(sorted(set(agencies))),
        ),
        institution_count=("_agency", "nunique"),
        total_pay=("Total Pay", sum),
    ).sort_values("institution_count", ascending=False)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Excluded surname tokens

    `surname_token_index` (see "Entity Resolution") only buckets records by
    surname-position tokens shared by `max_token_freq` records or fewer —
    anything above that threshold lands in `excluded_token_index` instead and
    is dropped from candidate-pair generation entirely, to keep the pairwise
    comparison in the cell below tractable.

    Clusters whose sole basis for matching is the high-frequency trailing name are excluded from our analysis.
    """)
    return


@app.cell
def _(df_er, excluded_token_index, institution_threshold, pd):
    def _is_blocking_blind_spot(name: str) -> bool:
        surname_tokens = name.split()[1:]
        return bool(surname_tokens) and all(
            t in excluded_token_index for t in surname_tokens
        )

    _blind_spot_frames = [
        group.assign(institution_count=group["_institution"].nunique())
        for _name, group in df_er.groupby("_name")
        if len(group) > 1
        and _is_blocking_blind_spot(_name)
        and group["_institution"].nunique() >= institution_threshold
    ]

    blind_spot_matches = (
        pd.concat(_blind_spot_frames)
        .sort_values("institution_count", ascending=False)
        .reset_index(drop=True)
        if _blind_spot_frames
        else pd.DataFrame()
    )
    return (blind_spot_matches,)


@app.cell
def _(blind_spot_matches, institution_threshold, max_token_freq, mo, pd):
    blind_spot_summary = (
        blind_spot_matches.groupby("_name")
        .agg(
            institutions=(
                "_institution",
                lambda agencies: " | ".join(sorted(set(agencies))),
            ),
            institution_count=("institution_count", "first"),
            record_count=("_record_id", "count"),
            job_titles=(
                "_job_title",
                lambda job_titles: " | ".join(sorted(set(job_titles))),
            ),
        )
        .sort_values("institution_count", ascending=False)
        .reset_index()
        if not blind_spot_matches.empty
        else pd.DataFrame()
    )

    mo.vstack(
        [
            mo.md(
                f"**{len(blind_spot_summary):,} exact-name matches** across "
                f"{institution_threshold}+ campuses are invisible to the "
                f"Entity Resolution pass because every surname-position token "
                f"in the name exceeds `max_token_freq` ({max_token_freq})."
            ),
            mo.ui.table(blind_spot_summary),
        ]
    )
    return (blind_spot_summary,)


@app.cell
def _(blind_spot_summary, mo):
    mo.vstack(
        [
            mo.md(
                "Excluded candidate cluster count for each high frequency surname"
            ),
            blind_spot_summary["_name"]
            .apply(lambda name: name.split()[-1])
            .value_counts(),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
