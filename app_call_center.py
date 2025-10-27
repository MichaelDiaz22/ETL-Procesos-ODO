import streamlit as st
import pandas as pd
import datetime

st.title("Call Report Analysis")
st.write("Upload a call report file (CSV) to analyze call data.")

uploaded_file = st.file_uploader("Upload CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write("File uploaded successfully!")
    st.write("DataFrame loaded:")
    st.dataframe(df.head())

    # Convert 'Ringing' and 'Talking' columns to timedelta objects
    df['Ringing'] = pd.to_timedelta(df['Ringing'], errors='coerce')
    df['Talking'] = pd.to_timedelta(df['Talking'], errors='coerce')

    # Convert timedelta to total seconds and then to minutes
    df['Tiempo total llamada (mins)'] = (df['Ringing'].dt.total_seconds() + df['Talking'].dt.total_seconds()) / 60

    st.write("Processed DataFrame with Total Call Time:")
    st.dataframe(df[['Ringing', 'Talking', 'Tiempo total llamada (mins)']].head())

    # Extract unique 'From' and 'To' values
    unique_from = df['From'].unique().tolist()
    unique_to = df['To'].unique().tolist()

    # Convert 'Call Time' to datetime and find min/max dates
    df['Call Time'] = pd.to_datetime(df['Call Time'], errors='coerce')
    min_date = df['Call Time'].min()
    max_date = df['Call Time'].max()

    st.write("Unique 'From' values:", unique_from[:10]) # Displaying first 10 for brevity
    st.write("Unique 'To' values:", unique_to[:10]) # Displaying first 10 for brevity
    st.write("Minimum Call Time:", min_date)
    st.write("Maximum Call Time:", max_date)


    st.sidebar.header("Filter Options")

    # Date range selector
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date) if pd.notnull(min_date) and pd.notnull(max_date) else (datetime.date.today(), datetime.date.today()),
        min_value=min_date if pd.notnull(min_date) else datetime.date(1900, 1, 1),
        max_value=max_date if pd.notnull(max_date) else datetime.date.today()
    )


    # Multiselect for 'From' values
    selected_from = st.sidebar.multiselect(
        "Select 'From' values",
        options=unique_from,
        default=unique_from
    )

    # Multiselect for 'To' values
    selected_to = st.sidebar.multiselect(
        "Select 'To' values",
        options=unique_to,
        default=unique_to
    )

    st.write("Selected Date Range:", date_range)
    st.write("Selected 'From' values:", selected_from[:10]) # Displaying first 10 for brevity
    st.write("Selected 'To' values:", selected_to[:10]) # Displaying first 10 for brevity

    filtered_df = df.copy()

    # Filter by date range
    if date_range is not None and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        filtered_df = filtered_df[(filtered_df['Call Time'] >= start_date) & (filtered_df['Call Time'] <= end_date)]

    # Filter by 'From' values
    if selected_from:
        filtered_df = filtered_df[filtered_df['From'].isin(selected_from)]

    # Filter by 'To' values
    if selected_to:
        filtered_df = filtered_df[filtered_df['To'].isin(selected_to)]

    st.write("Filtered DataFrame head:")
    st.dataframe(filtered_df.head())


    # Perform data aggregation only if filtered_df is not empty
    if not filtered_df.empty:
        # Group by 'From' and calculate the count of records and sum of 'Tiempo total llamada (mins)' for outgoing calls
        summary_outgoing = filtered_df.groupby('From').agg(
            {'Call Time': 'count', 'Tiempo total llamada (mins)': 'sum'}
        ).rename(columns={
            'Call Time': 'CANTIDAD SALIENTES',
            'Tiempo total llamada (mins)': 'TIEMPO SALIENTES(MINS)'
        })

        # Group by 'To' and calculate the count of records and sum of 'Tiempo total llamada (mins)' for incoming calls
        summary_incoming = filtered_df.groupby('To').agg(
            {'Call Time': 'count', 'Tiempo total llamada (mins)': 'sum'}
        ).rename(columns={
            'Call Time': 'CANTIDAD ENTRANTES',
            'Tiempo total llamada (mins)': 'TIEMPO ENTRANTES (MINS)'
        })

        # Merge the two tables based on the index (which represents the participant)
        # Use outer join to include all participants from both tables
        combined_summary = pd.merge(summary_incoming, summary_outgoing, left_index=True, right_index=True, how='outer')

        # Fill any missing values (NaN) with 0
        combined_summary = combined_summary.fillna(0)

        # Calculate the 'TIEMPO TOTAL OCUPADO (MINS)'
        combined_summary['TIEMPO TOTAL OCUPADO (MINS)'] = combined_summary['TIEMPO ENTRANTES (MINS)'] + combined_summary['TIEMPO SALIENTES(MINS)']

        st.header("Call Summary by Participant")
        st.dataframe(combined_summary)
    else:
        st.write("No data available after filtering.")