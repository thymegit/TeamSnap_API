import json
import requests
import pandas as pd

# Define your client credentials
client_id = 'client id'
client_secret = 'client secret'
code = 'application auth code'
redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
token_exchange_url = "https://auth.teamsnap.com/oauth/token"
api_url = "https://api.teamsnap.com/v3/"
team_id = "team ID"


# Exchange the authorization code for an access token
response = requests.post(
    token_exchange_url,
    data={
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
)

# Check response status and print raw response for debugging
print(f"HTTP status code: {response.status_code}")
response_content = response.text
print(response_content)

# Parse the response
token_response = response.json()

# Extract the access token
if 'access_token' in token_response:
    access_token = token_response['access_token']
    print(access_token)
else:
    print("Error fetching access token")
    print(token_response)

# Function to make authorized GET requests
def get_api(endpoint):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(f"{api_url}{endpoint}", headers=headers)
    return response
  
# Function to get team members
def get_team_members(team_id):
    members_response = get_api(f"members/search?team_id={team_id}")
    print(f"HTTP status code for members request: {members_response.status_code}")
    print(f"Members response content: {members_response.text}")
    
    if members_response.status_code == 200:
        members_json = members_response.json()
        members = members_json.get('collection', {}).get('items', [])
        member_details = []
        
        for member in members:
            member_data = {}
            for data_item in member['data']:
                member_data[data_item['name']] = data_item['value']
            member_details.append(member_data)
        
        return member_details
    else:
        print(f"Failed to fetch team members: {members_response.text}")
        return []

# Fetch team members
team_members = get_team_members(team_id)

# Define the date range from August 2023 to July 2024
start_date = "2023-08-01T00:00:00Z"
end_date = "2024-07-31T23:59:59Z"

# Get events within the specified date range
events_response = get_api(f"events/search?team_id={team_id}&started_after={start_date}&started_before={end_date}")
events_json = events_response.json()

# Extract the list of events
events = events_json['collection']['items']

# Function to extract event details
def extract_event_details(event):
    event_id = None
    event_name = None
    start_date = None
    end_date = None
    arrival_date = None
    game_event_name = None
    availability_link = None
    
    # Extract event data
    for data_item in event['data']:
        if data_item['name'] == 'id':
            event_id = data_item['value']
        if data_item['name'] == 'formatted_title':  # Checking formatted_title for event name
            event_name = data_item['value']
        if data_item['name'] == 'opponent_name':  # Checking opponent_name for game name
            game_event_name = data_item['value']
        if data_item['name'] == 'start_date':
            start_date = data_item['value']
        if data_item['name'] == 'end_date':
            end_date = data_item['value']
        if data_item['name'] == 'arrival_date':
            arrival_date = data_item['value']
    
    # Use game_event_name if event_name is not present or empty
    if not event_name:
        event_name = game_event_name
    
    # Extract availability link
    for link in event['links']:
        if link['rel'] == 'availabilities':
            availability_link = link['href']
    
    return {
        'id': event_id,
        'name': event_name,
        'start_date': start_date,
        'end_date': end_date,
        'arrival_date': arrival_date,
        'availability_link': availability_link
    }

# Extract details for all events
event_details = [extract_event_details(event) for event in events]

# Function to get event availabilities
def get_event_availabilities(availability_link):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(availability_link, headers=headers)
    if response.status_code == 200:
        availability_data = response.json()
        availabilities = availability_data['collection']['items']
        return availabilities
    else:
        return []

# Function to get team members
def get_team_members(team_id):
    members_response = get_api(f"teams/{team_id}/members")
    members_json = members_response.json()
    members = members_json['collection']['items']
    member_details = []
    
    for member in members:
        member_data = {}
        for data_item in member['data']:
            member_data[data_item['name']] = data_item['value']
        member_details.append(member_data)
    
    return member_details

# Fetch team members
team_members = get_team_members(team_id)

# Collect data for DataFrame
data = []

# Loop through each event to collect details and availabilities
for event in event_details:
    event_id = event['id']
    event_name = event['name']
    start_date = event['start_date']
    end_date = event['end_date']
    arrival_date = event['arrival_date']
    
    print(f"Processing Event: {event_id}, {event_name}, {start_date}")
    
    if event['availability_link']:
        availabilities = get_event_availabilities(event['availability_link'])
        if availabilities:
            for availability in availabilities:
                user_id = None
                status = None
                for data_item in availability['data']:
                    if data_item['name'] == 'member_id':  # Correctly extracting the user ID
                        user_id = data_item['value']
                    if data_item['name'] == 'status':
                        status = data_item['value']
                
                # Find member details for the given user ID
                member_details = next((member for member in team_members if member.get('id') == user_id), {})
                
                data.append({
                    'Event ID': event_id,
                    'Event Name': event_name,
                    'Start Date': start_date,
                    'End Date': end_date,
                    'Arrival Date': arrival_date,
                    'Game / Event Name': event_name,  # Use the label "Game / Event Name"
                    'User ID': user_id,
                    'Status': status,
                    'Member Name': member_details.get('first_name', '') + ' ' + member_details.get('last_name', ''),
                    'Member Email': member_details.get('email', '')
                })

# Create DataFrame
df = pd.DataFrame(data)

# Save DataFrame to a CSV file
df.to_csv('event_availabilities_aug2023_to_jul2024.csv', index=False)
  


