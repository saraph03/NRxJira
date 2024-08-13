import requests
import json

JIRA_BASE_URL = 'https://smartbygep.atlassian.net/rest/api/3/issue'
JIRA_SEARCH_URL = 'https://smartbygep.atlassian.net/rest/api/3/search'
JIRA_SEARCH_USER_URL = 'https://smartbygep.atlassian.net/rest/api/3/user/search'
JIRA_USERNAME = 'sara.phondge@gep.com'
JIRA_API_TOKEN = '#################################'
New_Relic_API_key = "#################################"
New_Relic_Account_ID = '#########3'
NRQL_QUERY = " SELECT count(*) FROM TransactionError where appName LIKE '%prod%us%invoice%' and appName NOT LIKE '%stg%' since 6 hours ago FACET appName, error.class, error.message, tags.product, tags.subproduct, tags.product_owner, tags.subproduct_owner, tags.Environment, tags.account  limit 50"

def run_nrql_query(nrql_query):
    url = f"https://insights-api.newrelic.com/v1/accounts/{New_Relic_Account_ID}/query"
    headers = {
        'Accept': 'application/json',
        'X-Query-Key': New_Relic_API_key
    }
    params = {
        'nrql': nrql_query
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching NRQL query results: {e}")
        return None

def get_jira_field_options(field_name):
    url = f"https://smartbygep.atlassian.net/rest/api/2/field/{field_name}/option"
    auth = (JIRA_USERNAME, JIRA_API_TOKEN)
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return []
def fetch_existing_jira_tickets():
    jql = 'project = AEH'
    params = {
        'jql': jql,
        'fields': 'summary,description',
        'maxResults': 1000
    }
    headers = {
        'Content-Type': 'application/json',
    }
    auth = (JIRA_USERNAME, JIRA_API_TOKEN)
    try:
        response = requests.get(JIRA_SEARCH_URL, headers=headers, auth=auth, params=params)
        response.raise_for_status()
        issues = response.json().get('issues', [])
        existing_tickets = [
            (issue['fields']['summary'], issue['fields']['description']['content'] if issue['fields'].get('description') else None)
            for issue in issues
        ]
        return existing_tickets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching existing Jira tickets: {e}")
        return []


def find_user_by_identifier(identifier):
    auth = (JIRA_USERNAME, JIRA_API_TOKEN)
    headers = {
        'Content-Type': 'application/json',
    }
    params = {
        'query': identifier,
        'maxResults': 1
    }
    try:
        print(f"Searching for user with identifier: {identifier}")
        response = requests.get(JIRA_SEARCH_USER_URL, headers=headers, auth=auth, params=params)
        response.raise_for_status()
        users = response.json()
        if users:
            return users[0]['accountId']
        else:
            print(f"No user found for identifier: {identifier}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error searching for user: {e}")
        return None

def create_jira_ticket(app_name, error_message, error_class, product_owner, module_option, actionable_team_option, project_key='AEH', issue_type='Bug'):
    auth = (JIRA_USERNAME, JIRA_API_TOKEN)
    headers = {
        'Content-Type': 'application/json',
    }
    assignee_id = find_user_by_identifier(product_owner)

    summary = f"{error_message[:50]}"  # Limit summary to 50 characters
    description = [
        {
            "type": "paragraph",
            "content": [
                {
                    "text": f"App Name: {app_name}",
                    "type": "text"
                }
            ]
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "text": f"Error Message: {error_message}",
                    "type": "text"
                }
            ]
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "text": f"Error Class: {error_class}",
                    "type": "text"
                }
            ]
        }
    ]

    if 'leo' or 'Leo' in app_name.lower():
        software_value = "GEP QUANTUM"
    elif 'nexxe' in app_name.lower():
        software_value = "GEP NEXXE"
    else:
        software_value = "GEP SMART" 
    
    environment_values = []
    if 'prod' in app_name.lower():
        environment_values.append({"value": "Production"})
    if 'uat' in app_name.lower():
        environment_values.append({"value": "UAT"})
    if 'qc' in app_name.lower():
        environment_values.append({"value": "QC"})
        
    print(f"Environments: {environment_values}")


    payload = {
        "fields": {
            "project": {
                "key": project_key
            },
            "summary": summary,  
            "description": {
                "type": "doc",
                "version": 1,
                "content": description
            },
            "issuetype": {
                "name": issue_type
            },
            "assignee": {"id": assignee_id},
            "customfield_15285" : {"value": module_option} if module_option else None,
            "customfield_15279" : {"value": actionable_team_option} if actionable_team_option else None,
            "customfield_15220" : {"value": software_value}, 
            "customfield_10203" : environment_values if environment_values else None  # Update with the actual field ID for 'environment'
        }
    }

    response = requests.post(JIRA_BASE_URL, auth=auth, headers=headers, data=json.dumps(payload))
    if response.status_code == 201:
        ticket_key = response.json()['key']
        print(f"Ticket created successfully: {ticket_key}")
    else:
        print(f"Failed to create ticket: {response.status_code}\n{response.text}")

def extract_app_name(description_content):
    for paragraph in description_content:
        if paragraph['type'] == 'paragraph':
            for content in paragraph['content']:
                if content['type'] == 'text' and content['text'].startswith("App Name: "):
                    return content['text'].split("App Name: ")[-1]
    return ""



def process_jira_tickets(json_response, existing_tickets):
    if 'facets' in json_response:
        facets = json_response['facets']
        for facet in facets:
            app_name = facet['name'][0]
            error_class = facet['name'][1]
            error_message = facet['name'][2]
            product_owner = facet['name'][4] if len(facet['name']) > 4 else "Unknown Owner"
            summary = f"{error_message[:50]}"  #  summary for comparison
            new_relic_data = run_nrql_query(NRQL_QUERY)
            if new_relic_data:
                product_names = None
                print("Extracted Product Names:", product_names)  # Print to inspect extracted product names

                actionable_team_option = None
                for facet in new_relic_data['facets']:
                    if facet['name'][3]:  # Check if the fourth element (tags.product) exists
                        product_names = facet['name'][3]
                    if facet['name'][5]:  # Check if the sixth element (tags.subproduct) exists
                        actionable_team_option = facet['name'][4]
                        
            print(f"App Name: {app_name}")
            print(f"Error Message: {error_message}") 
            print(f"Error Class: {error_class}")
            print(f"Product Owner: {product_owner}")
            print(f"Module: {product_names}")
           

            if any(summary in existing_summary and app_name == extract_app_name(existing_description) for existing_summary, existing_description in existing_tickets):
                print(f"Skipping duplicate ticket creation for {app_name} with error '{error_message}'")
                continue
            
            print(f"Creating Jira ticket for {app_name} with error '{error_message}'")
            create_jira_ticket(app_name, error_message, error_class, product_owner, product_names, actionable_team_option)

if __name__ == '__main__':
    existing_tickets = fetch_existing_jira_tickets()
    nrql_response = run_nrql_query(NRQL_QUERY)
    if nrql_response:
        process_jira_tickets(nrql_response, existing_tickets)
    else:
        print("Failed to fetch NRQL query results.")

