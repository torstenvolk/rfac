import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


# Load the data from GitHub
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/github/innovationgraph/main/data/topics.csv"
    data = pd.read_csv(url)

    # Create a 'year_quarter' column for the current year
    data['year_quarter'] = data['year'].astype(str) + 'Q' + data['quarter'].astype(str)

    # Create columns for the previous year and its corresponding quarter
    data['previous_year'] = data['year'] - 1
    data['previous_year_quarter'] = data['previous_year'].astype(str) + 'Q' + data['quarter'].astype(str)

    # Merge to find the previous year's data for the same quarter
    merged_data = pd.merge(data, data, left_on=['topic', 'iso2_code', 'previous_year_quarter'],
                           right_on=['topic', 'iso2_code', 'year_quarter'], how='left', suffixes=('', '_prev'))

    # Select and rename relevant columns
    merged_data = merged_data[['num_pushers', 'topic', 'iso2_code', 'year', 'quarter', 'num_pushers_prev']]
    merged_data.rename(columns={'num_pushers': 'num_pushers_current', 'num_pushers_prev': 'num_pushers_previous'},
                       inplace=True)

    # Fill missing values and calculate annual growth
    merged_data['num_pushers_previous'].fillna(0, inplace=True)
    merged_data['annual_growth'] = ((merged_data['num_pushers_current'] - merged_data['num_pushers_previous']) /
                                    merged_data['num_pushers_previous'].replace(0, np.nan)) * 100

    return merged_data


# Load the data
data = load_data()

# Streamlit app layout
st.write('GitHub Technology Data Visualization')

# Sidebar for filters and search
st.sidebar.header('Filters and Search')
selected_year = st.sidebar.selectbox('Year', sorted(data['year'].unique(), reverse=True))
selected_quarter = st.sidebar.selectbox('Quarter', sorted(data['quarter'].unique()))
selected_country = st.sidebar.selectbox('Country', sorted(data['iso2_code'].unique()))
search_string = st.sidebar.text_input('Search Topics (separate terms with commas)')

# Splitting the search string into multiple terms
search_terms = [term.strip().lower() for term in search_string.split(',')]

# Filtering the data
filtered_data = data[(data['year'] == selected_year) &
                     (data['quarter'] == selected_quarter) &
                     (data['iso2_code'] == selected_country) &
                     (data['topic'].str.lower().apply(lambda topic: any(term in topic for term in search_terms)))]

# Displaying data
st.write('Displaying data for:', selected_year, 'Q' + str(selected_quarter), '-', selected_country, 'with search:',
         search_string)
st.dataframe(filtered_data[['topic', 'num_pushers_current', 'num_pushers_previous', 'annual_growth']])


# Function to create horizontal bar chart
def create_bar_chart(data, column, title, ascending_order=True):
    sorted_data = data.sort_values(column, ascending=ascending_order)
    plt.figure(figsize=(10, 8))
    plt.barh(sorted_data['topic'], sorted_data[column], color='skyblue')
    plt.xlabel(column)
    plt.title(title)
    st.pyplot(plt)


# Function to create horizontal bar chart for two periods
def create_dual_bar_chart(data, current_column, previous_column, title):
    sorted_data = data.nlargest(25, current_column)
    sorted_data = sorted_data.sort_values(current_column, ascending=True)  # Sorting in ascending order
    topics = sorted_data['topic']
    current_values = sorted_data[current_column]
    previous_values = sorted_data[previous_column]

    # Setting the positions and width for the bars
    pos = np.arange(len(topics))
    bar_width = 0.35

    plt.figure(figsize=(10, 8))
    plt.barh(pos - bar_width / 2, current_values, bar_width, label='Current', color='skyblue')
    plt.barh(pos + bar_width / 2, previous_values, bar_width, label='Previous Year Same Quarter', color='lightgreen')
    plt.yticks(pos, topics)
    plt.xlabel('Number of Contributors')
    plt.title(title)
    plt.legend()

    st.pyplot(plt)


# Top 25 Fastest Growing Topics on GitHub
st.subheader('Top 25 Fastest Growing Topics on GitHub')
top_growth = filtered_data[filtered_data['annual_growth'] > 0].nlargest(25, 'annual_growth')
create_bar_chart(top_growth, 'annual_growth', 'Top 25 Fastest Growing Topics on GitHub', ascending_order=True)

# Top 25 Fastest Shrinking Topics on GitHub
st.subheader('Top 25 Fastest Shrinking Topics on GitHub')
top_decline = filtered_data[filtered_data['annual_growth'] < 0].nsmallest(25, 'annual_growth')
create_bar_chart(top_decline, 'annual_growth', 'Top 25 Fastest Shrinking Topics on GitHub', ascending_order=True)

# Top 25 Topics by Number of Contributors with Comparison to Previous Year
st.subheader('Top 25 Topics by Number of Contributors with Comparison to Previous Year')
top_pushers = filtered_data.nlargest(25, 'num_pushers_current')
create_dual_bar_chart(top_pushers, 'num_pushers_current', 'num_pushers_previous',
                      'Top 25 Topics by Number of Pushers and Previous Year Comparison')
