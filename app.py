import streamlit as st
import pandas as pd

st.set_page_config(page_title="GC Compound Finder", layout="centered")

st.title("GC Compound Name Finder")

# Load Excel file from repo
file_path = "RCPPR_GC_DATABASE.xlsx"

@st.cache_data
def load_data():
    df = pd.read_excel(file_path)
    df['Retention Time'] = pd.to_numeric(df['Retention Time'], errors='coerce')
    df.dropna(subset=['Retention Time'], inplace=True)
    return df

df = load_data()

# Input
input_rt = st.number_input("Enter Retention Time:", min_value=0.0, format="%.4f")

if st.button("Find Compound Name"):   # ✅ changed here

    df['diff'] = (df['Retention Time'] - input_rt).abs()

    closest_peaks = df.sort_values(by='diff').head(3)

    closest_peaks_display = closest_peaks.rename(columns={
        'Compound Name': 'NAME',
        'Retention Time': 'RETENTION TIME'
    })

    exact_match_found = (df['Retention Time'] == input_rt).any()

    if exact_match_found:
        matched_entries = df[df['Retention Time'] == input_rt]
        matched_names = matched_entries['Compound Name'].tolist()

        matched_display = matched_entries.rename(columns={
            'Compound Name': 'NAME',
            'Retention Time': 'RETENTION TIME'
        })

        st.success(f"Compound identified: {', '.join(matched_names)}")

        st.subheader("Matched Compound(s)")
        st.dataframe(matched_display[['NAME', 'RETENTION TIME']])

    else:
        st.warning(
            f"No exact compound found for RT = {input_rt}. Showing closest matches."
        )

        st.subheader("Nearest Compounds")
        st.dataframe(closest_peaks_display[['NAME', 'RETENTION TIME']])
