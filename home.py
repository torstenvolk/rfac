import streamlit as st
import praw
from datetime import datetime
import pandas as pd
from st_aggrid import AgGrid
import openai

st.title = 'Reddit Posts and Comments'

# Load the API key from Streamlit secrets
client_id = st.secrets["reddit"]["client_id"]
client_secret = st.secrets["reddit"]["client_secret"]
username = st.secrets["reddit"]["username"]
password = st.secrets["reddit"]["password"]
user_agent = st.secrets["reddit"]["user_agent"]

# Initialize the Reddit instance
reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     username=username,
                     password=password,
                     user_agent=user_agent)

# Define a function to retrieve the last 10 submissions for a given subreddit


@st.cache_data
def get_submissions(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    submissions = subreddit.new(limit=10)
    submissions_with_comments = []
    for submission in submissions:
        comments = [comment.body for comment in submission.comments.list()[:10]]  # Fetching top 10 comments
        submission_with_comments = {
            "Subreddit": subreddit_name,
            "Title": submission.title,
            "Author": str(submission.author),
            "Score": submission.score,
            "Number of Comments": submission.num_comments,
            "Timestamp": datetime.utcfromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
            "Comments": comments
        }
        submissions_with_comments.append(submission_with_comments)
    return submissions_with_comments

@st.cache_data
def get_flattened_submissions(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    submissions = subreddit.new(limit=10)
    flattened_data = []
    for submission in submissions:
        # Add the main post
        flattened_data.append({
            "Type": "Post",
            "Subreddit": subreddit_name,
            "Title": submission.title,
            "Author": str(submission.author),
            "Score": submission.score,
            "Comments": "Post",
            "Timestamp": datetime.utcfromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S')
        })
        # Add top 10 comments
        for comment in submission.comments.list()[:10]:
            flattened_data.append({
                "Type": "Comment",
                "Subreddit": subreddit_name,
                "Title": submission.title,  # Linking comment to the post title
                "Author": str(comment.author),
                "Score": comment.score,
                "Comments": comment.body,
                "Timestamp": datetime.utcfromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S')
            })
    return flattened_data



# Set page configuration
st.set_page_config(layout='wide')


# Check if data is already loaded in the session state
if 'loaded_data' not in st.session_state:
    subreddits = ["kubernetes", "devops", "sysadmin"]
    all_data = []
    for subreddit_name in subreddits:
        flattened_submissions = get_flattened_submissions(subreddit_name)
        all_data.extend(flattened_submissions)

    st.session_state['loaded_data'] = pd.DataFrame(all_data)

# Add a heading for the AgGrid table
st.header('Subreddit Posts and Comments')

# Use the data from the session state for the AgGrid
grid_options = {
    'columnDefs': [
        {'headerName': "Type", 'field': "Type"},
        {'headerName': "Subreddit", 'field': "Subreddit"},
        {'headerName': "Title", 'field': "Title"},
        {'headerName': "Author", 'field': "Author"},
        {'headerName': "Score", 'field': "Score"},
        {'headerName': "Comments", 'field': "Comments"},
        {'headerName': "Timestamp", 'field': "Timestamp"}
    ],
    'defaultColDef': {
        'sortable': True,
        'filter': True,
        'enableCellTextSelection': True  # Allows text selection in cells
    },
    'clipboard': {
        'enabled': True,  # Enable clipboard interactions
        'copyRowsToClipboard': True,  # Copy entire rows to the clipboard
        'copyWithHeaders': True,  # Copy headers along with data
    },
}

AgGrid(st.session_state['loaded_data'], gridOptions=grid_options, enable_enterprise_modules=True)


# OpenAI API key
openai.api_key = st.secrets["openai"]["openai_api_key"]

def summarize_text(text):
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview",  # Specify the GPT-4 chat model
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Summarize the following information:\n\n{text}"}
        ]
    )
    return response['choices'][0]['message']['content']

def get_aggregated_subreddit_data(df, subreddit):
    subreddit_data = df[df['Subreddit'] == subreddit]
    unique_titles_comments = subreddit_data[['Title', 'Comments']].drop_duplicates()
    aggregated_text = '\n'.join(unique_titles_comments.apply(lambda x: f"Title: {x['Title']}\nComment: {x['Comments']}", axis=1))
    return aggregated_text

def get_unique_titles_comments(df):
    unique_text = ""
    for subreddit in df['Subreddit'].unique():
        titles_comments = df[df['Subreddit'] == subreddit][['Title', 'Comments']]
        titles_comments = titles_comments.drop_duplicates()
        concatenated = '\n'.join(titles_comments.apply(lambda x: f"Title: {x['Title']}\nComment: {x['Comments']}", axis=1))
        unique_text += f"Subreddit: {subreddit}\n{concatenated}\n\n"
    return unique_text


if st.button("Summarize Subreddit Data"):
    subreddits = st.session_state['loaded_data']['Subreddit'].unique()
    total = len(subreddits)
    progress_bar = st.progress(0)
    summaries = {}

    for i, subreddit in enumerate(subreddits):
        aggregated_text = get_aggregated_subreddit_data(st.session_state['loaded_data'], subreddit)
        summary = summarize_text(aggregated_text)
        summaries[subreddit] = summary

        # Update the progress bar
        progress = int((i + 1) / total * 100)
        progress_bar.progress(progress)

    for subreddit, summary in summaries.items():
        st.subheader(f"Summary for {subreddit}")
        st.text_area(f"{subreddit} Summary", summary, height=150)

    # Complete the progress bar
    progress_bar.progress(100)