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
patient_id = 20860460
start_date = "2024-10-30T00:00:00"
end_date = "2024-08-02T00:00:00"

# Define the XML payload with correct SOAP 1.1 envelope for Search Visits
soap_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <SearchCaregivers xmlns="https://www.hhaexchange.com/apis/hhaws.integration">
      <Authentication>
        <AppName>{app_name}</AppName>
        <AppSecret>{app_secret}</AppSecret>
        <AppKey>{app_key}</AppKey>
      </Authentication>
      <SearchFilters>
        <CaregiverCode>ANT-</CaregiverCode>
      </SearchFilters>
    </SearchCaregivers>
  </soap:Body>
</soap:Envelope>"""

# Define the headers, including content type for XML and SOAPAction
headers = {
    'Content-Type': 'text/xml; charset=utf-8',  # Set content type to XML for SOAP 1.1
    'SOAPAction': '"https://www.hhaexchange.com/apis/hhaws.integration/SearchCaregivers"',
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
namespace = {'ns1': "https://www.hhaexchange.com/apis/hhaws.integration"}  # Replace with the actual namespace URI

# Find all `CaregiverTeamID` elements, using the namespace
caregiver_ids = [elem.text for elem in root.findall('.//ns1:CaregiverID', namespaces=namespace)]

visit_data_list = []


def filter_caregiver(caregiver_id):
    soap_payload = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetCaregiverDemographics  xmlns="https://www.hhaexchange.com/apis/hhaws.integration">
          <Authentication>
            <AppName>{app_name}</AppName>
            <AppSecret>{app_secret}</AppSecret>
            <AppKey>{app_key}</AppKey>
          </Authentication>
          <CaregiverInfo>
            <ID>{caregiver_id}</ID>
          </CaregiverInfo>
        </GetCaregiverDemographics >
      </soap:Body>
    </soap:Envelope>"""

    # Define the headers, including content type for XML and SOAPAction
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',  # Set content type to XML for SOAP 1.1
        'SOAPAction': '"https://www.hhaexchange.com/apis/hhaws.integration/GetCaregiverDemographics "',
        # Correct the SOAPAction header for Search Visits
    }

    # Use the general endpoint URL for the SOAP service
    endpoint_url = 'https://app.hhaexchange.com/integration/ent/v1.8/ws.asmx'

    response = requests.post(endpoint_url, data=soap_payload, headers=headers)

    if response.status_code != 200:
        # Print the error code and response content if there was an error
        print(f"Error {response.status_code}: {response.text}")

    root = ET.fromstring(response.content)

    # Define the namespaces if needed
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


async def get_caregiver_notes(session, caregiver_id):
    # Define the XML payload with correct SOAP 1.1 envelope for Search Visits
    soap_payload = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetCaregiverNotes xmlns="https://www.hhaexchange.com/apis/hhaws.integration">
          <Authentication>
            <AppName>{app_name}</AppName>
            <AppSecret>{app_secret}</AppSecret>
            <AppKey>{app_key}</AppKey>
          </Authentication>
            <CaregiverID>{caregiver_id}</CaregiverID>
            <ModifiedAfter>{start_date}</ModifiedAfter>
        </GetCaregiverNotes>
      </soap:Body>
    </soap:Envelope>"""

    # Define the headers, including content type for XML and SOAPAction
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',  # Set content type to XML for SOAP 1.1
        'SOAPAction': '"https://www.hhaexchange.com/apis/hhaws.integration/GetCaregiverNotes"',
        # Correct the SOAPAction header for Search Visits
    }

    # Use the general endpoint URL for the SOAP service
    endpoint_url = 'https://app.hhaexchange.com/integration/ent/v1.8/ws.asmx'

    async with session.post(endpoint_url, data=soap_payload, headers=headers) as response:
        response_text = await response.text()
        namespace = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                     'ns': 'https://www.hhaexchange.com/apis/hhaws.integration'}
        root = ET.fromstring(response_text)
        caregiver_notes = root.find('.//ns:VisitInfo', namespace)
        if caregiver_notes is not None:
            #     parsed_data = {
            #         'CaregiverCode': caregiver_notes.find('ns:Caregiver/ns:CaregiverCode', namespace).text,
            #         'VisitStartTime': visit_info.find('ns:VisitStartTime', namespace).text,
            #         'VisitEndTime': visit_info.find('ns:VisitEndTime', namespace).text,
            #         'IsMissedVisit': visit_info.find('ns:IsMissedVisit', namespace).text,
            #         'ServiceHours': visit_info.find('ns:Payroll/ns:ServiceHours', namespace).text,
            #     }
            return caregiver_notes
        return None


# Main function to handle asynchronous tasks
async def main(caregiver_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [get_caregiver_notes(session, caregiver_id) for caregiver_id in caregiver_ids]
        results = await asyncio.gather(*tasks)
        # Filter out any None results
        results = [result for result in results if result is not None]
        # Create a DataFrame
        notes_df = pd.DataFrame(results)
        return notes_df

# start_time = time.time()
# notes_df = asyncio.run(main(caregiver_ids))

# end_time = time.time()

# time_for_report = start_time - end_time
