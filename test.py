import APIkeys
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import asyncio
import aiohttp

app_name = APIkeys.app_name
app_secret = APIkeys.app_secret
app_key = APIkeys.app_key

# Define the XML payload with correct SOAP 1.1 envelope for Search Visits
soap_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetCaregiverDemographics xmlns="https://www.hhaexchange.com/apis/hhaws.integration">
      <Authentication>
        <AppName>{app_name}</AppName>
        <AppSecret>{app_secret}</AppSecret>
        <AppKey>{app_key}</AppKey>
      </Authentication>
      <CaregiverInfo>
        <ID>1068972</ID>
      </CaregiverInfo>
    </GetCaregiverDemographics>
  </soap:Body>
</soap:Envelope>"""

# Define the headers, including content type for XML and SOAPAction
headers = {
    'Content-Type': 'text/xml; charset=utf-8',  # Set content type to XML for SOAP 1.1
    'SOAPAction': '"https://www.hhaexchange.com/apis/hhaws.integration/GetCaregiverDemographics"',
    # Correct the SOAPAction header for Search Visits
}

# Use the general endpoint URL for the SOAP service
endpoint_url = 'https://app.hhaexchange.com/integration/ent/v1.8/ws.asmx'

response = requests.post(endpoint_url, data=soap_payload, headers=headers)

if response.status_code != 200:
    # Print the error code and response content if there was an error
    print(f"Error {response.status_code}: {response.text}")

root = ET.fromstring(response.content)
xml_string = ET.tostring(root, encoding='utf-8').decode('utf-8')

# Define the namespace if needed
namespaces = {
    'ns0': 'http://schemas.xmlsoap.org/soap/envelope/',
    'ns1': 'https://www.hhaexchange.com/apis/hhaws.integration'
}

# Extract Team ID and Team Name
team_id = root.find('.//ns1:Team/ns1:ID', namespaces=namespaces).text
team_name = root.find('.//ns1:Team/ns1:Name', namespaces=namespaces).text

# Extract Status (ID and Name)
status_id = root.find('.//ns1:Status/ns1:ID', namespaces=namespaces).text
status_name = root.find('.//ns1:Status/ns1:Name', namespaces=namespaces).text

# Extract Caregiver Code
caregiver_code = root.find('.//ns1:CaregiverCode', namespaces=namespaces).text
