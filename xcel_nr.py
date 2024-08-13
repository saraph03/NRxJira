import pandas as pd
import requests
import json

# Load Excel file
df = pd.read_excel('tags_data.xlsx')

# Convert to JSON
json_data = df.to_json(orient='records')

# Save JSON data to a file (optional)
with open('tags_data.json', 'w') as f:
    f.write(json_data)

# Load JSON data
with open('tags_data.json') as f:
    tags_data = json.load(f)

# New Relic API endpoint and headers
api_key = "########################################"
headers = {
    "Api-Key": api_key,
    "Content-Type": "application/json"
}

# Function to get Entity ID by App Name using GraphQL
def get_entity_id_by_app_name(app_name):
    url = "https://api.newrelic.com/graphql"
    query = """
    {
      actor {
        entitySearch(query: "name = '%s'") {
          results {
            entities {
              guid
              name
            }
          }
        }
      }
    }
    """ % app_name
    response = requests.post(url, headers=headers, json={'query': query})
    if response.status_code == 200:
        entities = response.json().get('data', {}).get('actor', {}).get('entitySearch', {}).get('results', {}).get('entities', [])
        if entities:
            return entities[0]['guid']
    print(f"Failed to retrieve entity ID for app name {app_name}: {response.status_code}, {response.text}")
    return None

# Function to add tags to an entity using GraphQL
def add_tags(entity_id, tags):
    url = "https://api.newrelic.com/graphql"
    mutation = """
    mutation {
      taggingAddTagsToEntity(guid: "%s", tags: [
        {key: "product", values: ["%s"]},
        {key: "subproduct", values: ["%s"]},
        {key: "product_owner", values: ["%s"]},
        {key: "subproduct_owner", values: ["%s"]}
        
      ]) {
        errors {
          message
        }
      }
    }
    """ % (
        entity_id,
        tags['tags.product'],
        tags['tags.subproduct'],
        tags['tags.product_owner'],
        tags['tags.subproduct_owner']
      #  tags['tags.environment'],
      #  tags['tags.account'],
    )
    response = requests.post(url, headers=headers, json={'query': mutation})
    response_data = response.json()
    if response.status_code == 200:
        errors = response_data.get('data', {}).get('taggingAddTagsToEntity', {}).get('errors', [])
        if not errors:
            print("Response data:", response_data)
            print(f"Successfully added tags to entity {entity_id}")
        else:
            print(f"Failed to add tags to entity {entity_id}: {errors}")
    else:
        print(f"Failed to add tags to entity {entity_id}: {response.status_code}, {response.text}")
        print("Response data:", response_data)

# Iterate over the JSON data and add tags to each entity
for record in tags_data:
    entity_id = get_entity_id_by_app_name(record['appName'])
    if entity_id:
        tags = {
            "tags.product": record.get('tags.product'),
            "tags.subproduct": record.get('tags.subproduct'),
            "tags.product_owner": record.get('tags.product_owner'),
            "tags.subproduct_owner": record.get('tags.subproduct_owner')
          #  "tags.environment": record.get('tags.environment'),
          #  "tags.account": record.get('tags.account'),
        }

        # Print tags dictionary for debugging
        print(f"Tags for entity {entity_id}: {tags}")

        # Check for missing keys and print them
        missing_keys = [key for key, value in tags.items() if value is None]
        if missing_keys:
            print(f"Missing keys for {record['appName']}: {missing_keys}")

        add_tags(entity_id, tags)
