import requests
import pandas as pd
import random
import string
from azure.identity import AzureCliCredential

CSV_FILE = "users.csv"
GRAPH_API = "https://graph.microsoft.com/v1.0"

TENANT_DOMAIN = "InsertYourTenantDomainHere.com"

credential = AzureCliCredential()
#Install Azure CLI on your local machine first
#Make sure you are logged in to your azure account using the "az login" command
#This script uses the context of the logged in azure account in your terminal/cmd
#Make sure your account has sufficient privileges to be able to create users in your directory

token = credential.get_token("https://graph.microsoft.com/.default").token
headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

def generate_password(length=14):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(random.choice(chars) for _ in range(length))

def get_group_id(group_name):
    url = f"{GRAPH_API}/groups?$filter=displayName eq '{group_name}'"
    response = requests.get(url, headers=headers).json()
    groups = response.get("value", [])
    if groups:
        return groups[0]["id"]
    return None

def create_user(first, last, email, id_number, password):
    upn_local = email.split("@")[0]
    user_principal_name = f"{upn_local}@{TENANT_DOMAIN}"  # enforce valid tenant domain

    user_data = {
        "accountEnabled": True,
        "displayName": f"{first} {last}",
        "mailNickname": upn_local,
        "userPrincipalName": user_principal_name,
        "givenName": first,
        "surname": last,
        "employeeId": str(id_number),
        "mail": email,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": password
        }
    }

    response = requests.post(f"{GRAPH_API}/users", headers=headers, json=user_data)
    if response.status_code == 201:
        return response.json()["id"]
    else:
        print(f"Failed to create user {email}: {response.text}")
        return None

def add_user_to_group(user_id, group_id):
    url = f"{GRAPH_API}/groups/{group_id}/members/$ref"
    data = {"@odata.id": f"{GRAPH_API}/directoryObjects/{user_id}"}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in (204, 201):
        return True
    else:
        print(f"Failed to add user to group: {response.text}")
        return False

df = pd.read_csv(CSV_FILE)
results = []

for _, row in df.iterrows():
    password = generate_password()
    user_id = create_user(row["FirstName"], row["LastName"], row["Email"], row["IDNumber"], password)

    if user_id:
        group_id = get_group_id(row["Group"])
        if group_id:
            add_user_to_group(user_id, group_id)
            print(f"Created {row['Email']} and added to {row['Group']}")
        else:
            print(f"Group {row['Group']} not found for {row['Email']}")

        results.append({
            "FirstName": row["FirstName"],
            "LastName": row["LastName"],
            "Email": row["Email"],
            "Group": row["Group"],
            "EmployeeId": row["IDNumber"],
            "GeneratedPassword": password
        })

pd.DataFrame(results).to_csv("created_users_report.csv", index=False)
print("User creation report saved to created_users_report.csv")
