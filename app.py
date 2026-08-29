import streamlit as st
import pandas as pd
import numpy as np
import json
import zipfile
import requests
import io

# ---------------- LOAD DATABASE FROM GITHUB ZIP ---------------- #
@st.cache_data
def load_database():
    url = "https://raw.githubusercontent.com/Ganeshkumar-byte/GC-MS/main/MoNA-export-GC-MS_Spectra-json.zip"

    try:
        response = requests.get(url)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:

            # ✅ Correct file path (based on your debug output)
            json_path = "MoNA-export-GC-MS_Spectra.json"

            if json_path not in z.namelist():
                st.error("❌ JSON file not found inside ZIP")
                st.write("Files inside ZIP:", z.namelist())
                return []

            with z.open(json_path) as f:
                data = json.load(f)

        return data

    except Exception as e:
        st.error(f"Error loading database: {e}")
        return []


# ---------------- MATCH FUNCTION ---------------- #
def calculate_match_factor(query_peaks, library_peaks):
    all_mz = set(query_peaks.keys()).union(set(library_peaks.keys()))

    numerator = 0
    sum_q_sq = 0
    sum_l_sq = 0

    for mz in all_mz:
        q_int = query_peaks.get(mz, 0)
        l_int = library_peaks.get(mz, 0)

        w_q = (mz ** 0.5) * (q_int ** 0.5)
        w_l = (mz ** 0.5) * (l_int ** 0.5)

        numerator += (w_q * w_l)
        sum_q_sq += (w_q ** 2)
        sum_l_sq += (w_l ** 2)

    if sum_q_sq == 0 or sum_l_sq == 0:
        return 0

    score = (numerator**2) / (sum_q_sq * sum_l_sq)
    return round(score * 1000)


# ---------------- PARSE FUNCTIONS ---------------- #
def parse_spectrum_string(spectrum_str):
    peaks_dict = {}

    if not isinstance(spectrum_str, str):
        return peaks_dict

    for peak_pair in spectrum_str.split(' '):
        if ':' in peak_pair:
            try:
                mz_str, intensity_str = peak_pair.split(':')
                mz = int(float(mz_str))
                intensity = float(intensity_str)
                peaks_dict[mz] = intensity
            except:
                continue

    return peaks_dict


def parse_user_input(input_text):
    peaks = {}
    pairs = input_text.split(',')

    for pair in pairs:
        if ':' in pair:
            try:
                mz, intensity = pair.split(':')
                peaks[int(float(mz.strip()))] = float(intensity.strip())
            except:
                continue

    return peaks


# ---------------- MOLECULAR WEIGHT HELPER ---------------- #
def get_molecular_weight(actual):
    """Extracts molecular weight from a compound's metaData block."""
    mw = None
    if 'metaData' in actual:
        for item in actual['metaData']:
            name = str(item.get('name', '')).lower()
            if name in ['total exact mass', 'molecular weight', 'exact mass', 'mw']:
                try:
                    mw = float(item.get('value'))
                    break
                except (TypeError, ValueError):
                    continue
    return mw


# ---------------- MATCH SEARCH (SPECTRAL) ---------------- #
def find_top_matches(manual_data, database):

    results = []

    if isinstance(database, dict):
        compounds_to_process = database.values()
    elif isinstance(database, list):
        compounds_to_process = database
    else:
        st.error(f"Unexpected database type: {type(database)}")
        return pd.DataFrame()

    for compound_entry in compounds_to_process:

        if not isinstance(compound_entry, dict):
            continue

        try:
            # Extract compound details
            if 'compound' in compound_entry and len(compound_entry['compound']) > 0:
                actual = compound_entry['compound'][0]
            else:
                actual = {}

            # Name
            name = 'Unknown'
            if 'names' in actual and len(actual['names']) > 0:
                name = actual['names'][0].get('name', 'Unknown')

            # Formula
            formula = 'N/A'
            if 'metaData' in actual:
                for item in actual['metaData']:
                    if item.get('name') == 'molecular formula':
                        formula = item.get('value', 'N/A')
                        break

            # Spectrum
            spectrum_str = compound_entry.get('spectrum', '')
            library_peaks = parse_spectrum_string(spectrum_str)

            if not library_peaks:
                continue

            score = calculate_match_factor(manual_data, library_peaks)

            results.append({
                "Name": name,
                "Formula": formula,
                "Match Score": score
            })

        except:
            continue

    # ✅ Prevent crash if empty
    if len(results) == 0:
        st.warning("⚠️ No matches found. Check your input or database.")
        return pd.DataFrame(columns=["Name", "Formula", "Match Score"])

    df = pd.DataFrame(results)
    return df.sort_values(by="Match Score", ascending=False).head(5)


# ---------------- SEARCH BY MOLECULAR WEIGHT ---------------- #
def find_by_molecular_weight(target_mw, database, tolerance=0.5):
    results = []

    if isinstance(database, dict):
        compounds_to_process = database.values()
    elif isinstance(database, list):
        compounds_to_process = database
    else:
        st.error(f"Unexpected database type: {type(database)}")
        return pd.DataFrame(), []

    for compound_entry in compounds_to_process:
        if not isinstance(compound_entry, dict):
            continue

        try:
            if 'compound' in compound_entry and len(compound_entry['compound']) > 0:
                actual = compound_entry['compound'][0]
            else:
                actual = {}

            mw = get_molecular_weight(actual)
            if mw is None:
                continue

            if abs(mw - target_mw) > tolerance:
                continue

            name = 'Unknown'
            if 'names' in actual and len(actual['names']) > 0:
                name = actual['names'][0].get('name', 'Unknown')

            formula = 'N/A'
            if 'metaData' in actual:
                for item in actual['metaData']:
                    if item.get('name') == 'molecular formula':
                        formula = item.get('value', 'N/A')
                        break

            spectrum_str = compound_entry.get('spectrum', '')
            peaks = parse_spectrum_string(spectrum_str)

            results.append({
                "Name": name,
                "Formula": formula,
                "Molecular Weight": mw,
                "Num Peaks": len(peaks),
                "Spectrum": spectrum_str
            })

        except Exception:
            continue

    if len(results) == 0:
        return pd.DataFrame(columns=["Name", "Formula", "Molecular Weight", "Num Peaks", "Spectrum"]), []

    df = pd.DataFrame(results).sort_values(by="Molecular Weight")
    return df, results


# ---------------- STREAMLIT UI ---------------- #

# Page config (tab title + layout)
st.set_page_config(
    page_title="Entity 1",
    layout="centered"
)

# ---- HEADER WITH LOGO ----
col1, col2 = st.columns([1, 4])

with col1:
    st.image("logo.jpg", width=80)   # make sure logo file name matches

with col2:
    st.markdown("## Entity 1")
    st.markdown("### GC-MS Spectral Matcher")

# Load database once, shared by both tools below
with st.spinner("Loading database..."):
    database = load_database()

if not database:
    st.error("❌ Database failed to load. Check ZIP or URL.")
    st.stop()
else:
    st.success(f"✅ Database loaded ({len(database)} entries)")

# ---- TABS: keep the two tools separate but in one app ----
tab1, tab2 = st.tabs(["🔍 Spectral Match", "⚖️ Search by Molecular Weight"])

# ================= TAB 1: SPECTRAL MATCH ================= #
with tab1:
    st.write("Enter peaks like: `43:100, 70:12, 61:11`")

    user_input = st.text_area(
        "Enter m/z : intensity values",
        "43:100, 70:12, 61:11, 88:3, 41:8, 42:6",
        key="spectral_input"
    )

    if st.button("Find Matches", key="spectral_button"):

        if not user_input:
            st.warning("Please enter peak values.")
        else:
            with st.spinner("Matching spectra..."):

                query_peaks = parse_user_input(user_input)

                if not query_peaks:
                    st.error("Invalid input format!")
                else:
                    matches = find_top_matches(query_peaks, database)

                    st.success("Top Matches Found!")
                    st.dataframe(matches)

# ================= TAB 2: MOLECULAR WEIGHT SEARCH ================= #
with tab2:
    st.write("Find all compounds (and their spectra) at a given molecular weight.")

    target_mw = st.number_input("Enter Molecular Weight (Da)", min_value=0.0, value=100.0, step=0.1)
    tolerance = st.number_input("Tolerance (± Da)", min_value=0.0, value=0.5, step=0.1)

    if st.button("Find Compounds by MW", key="mw_button"):
        with st.spinner("Searching database..."):
            mw_df, mw_results = find_by_molecular_weight(target_mw, database, tolerance)

        if mw_df.empty:
            st.warning(f"No compounds found with molecular weight {target_mw} ± {tolerance}")
        else:
            st.success(f"Found {len(mw_df)} compound(s)")
            st.dataframe(mw_df[["Name", "Formula", "Molecular Weight", "Num Peaks"]])

            # Store results in session state so selection persists across reruns
            st.session_state["mw_results"] = mw_results
            st.session_state["mw_names"] = mw_df["Name"].tolist()

    # Show spectrum viewer if we have results from a previous search
    if "mw_results" in st.session_state and st.session_state["mw_results"]:
        selected_name = st.selectbox(
            "View spectrum for:",
            st.session_state["mw_names"],
            key="mw_selectbox"
        )
        selected_row = next(
            r for r in st.session_state["mw_results"] if r["Name"] == selected_name
        )

        st.write(
            f"**{selected_row['Name']}** "
            f"({selected_row['Formula']}, MW {selected_row['Molecular Weight']})"
        )

        peaks = parse_spectrum_string(selected_row["Spectrum"])
        if peaks:
            peaks_df = pd.DataFrame(sorted(peaks.items()), columns=["m/z", "Intensity"])
            st.bar_chart(peaks_df.set_index("m/z"))
            st.dataframe(peaks_df)
        else:
            st.info("No parsable spectrum peaks for this compound.")

    # Optional debug helper — check actual metaData key names in the JSON
    with st.expander("🔧 Debug: inspect metaData keys (optional)"):
        if st.checkbox("Show sample metaData"):
            sample = database[0] if isinstance(database, list) else list(database.values())[0]
            actual = sample.get('compound', [{}])[0]
            st.write(actual.get('metaData', []))
