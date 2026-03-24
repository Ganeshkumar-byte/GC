import streamlit as st
import pandas as pd

st.set_page_config(page_title="GC Retention Finder", layout="centered")

st.title("GC Retention Time Finder")

# Load Excel file directly from repo
file_path = "RCPPR_GC_DATABASE.xlsx"

@st.cache_data
def load_data():
    df = pd.read_excel(file_path)
    df['Retention Time'] = pd.to_numeric(df['Retention Time'], errors='coerce')
    df.dropna(subset=['Retention Time'], inplace=True)
    return df

df = load_data()

# User input
input_rt = st.number_input("Enter retention time:", min_value=0.0, format="%.4f")

if st.button("Find Peaks"):

    # Calculate difference
    df['diff'] = (df['Retention Time'] - input_rt).abs()

    # Sort nearest
    closest_peaks = df.sort_values(by='diff').head(3)

    closest_peaks_display = closest_peaks.rename(columns={
        'Compound Name': 'NAME',
        'Retention Time': 'RETENTION TIME'
    })

    # Exact match check
    exact_match_found = (df['Retention Time'] == input_rt).any()

    if exact_match_found:
        matched_entries = df[df['Retention Time'] == input_rt]
        matched_names = matched_entries['Compound Name'].tolist()

        matched_display = matched_entries.rename(columns={
            'Compound Name': 'NAME',
            'Retention Time': 'RETENTION TIME'
        })

        st.success(f"Exact match found for: {', '.join(matched_names)}")

        st.subheader("Exact Match(es)")
        st.dataframe(matched_display[['NAME', 'RETENTION TIME']])

    else:
        st.warning(
            f"No exact match found for {input_rt}. "
            "Elution may vary depending on conditions."
        )

        st.subheader("Nearest 3 Peaks")
        st.dataframe(closest_peaks_display[['NAME', 'RETENTION TIME']])
